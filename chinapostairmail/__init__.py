#!/usr/bin/python

import Tkinter as tk
import shelve
import thread
import time
import os

from antigate import AntiGate
from grab import Grab, tools
import tkMessageBox as box


NAME, KEY, STATUS = range(3)


def center(win):
    win.update_idletasks()
    frm_width = win.winfo_rootx() - win.winfo_x()
    win_width = win.winfo_width() + (frm_width * 2)
    title_bar_height = win.winfo_rooty() - win.winfo_y()
    win_height = win.winfo_height() + (title_bar_height + frm_width)
    x = (win.winfo_screenwidth() / 2) - (win_width / 2)
    y = (win.winfo_screenheight() / 2) - (win_height / 2)
    geom = (win.winfo_width(), win.winfo_height(), x, y)
    win.geometry('{0}x{1}+{2}+{3}'.format(*geom))


class SettingsDialog():

    def __init__(self, parent, callback, api_key=''):
        self.callback = callback

        top = self.top = tk.Toplevel(parent)
        label = tk.Label(top, text='AntiGate.com API key:')
        label.pack()

        self.key = tk.Entry(top)
        self.key.pack()
        if api_key:
            self.key.insert(0, api_key)

        tk.Button(top, text='Save', command=self.send).pack()
        tk.Button(top, text='Close', command=self.close).pack()

        center(top)

    def close(self):
        self.top.destroy()

    def send(self):
        if self.key.get():
            self.callback(self.key.get())
            self.top.destroy()
        else:
            box.showerror("Error", "API key is required!")


class TrackAddDialog():
    def __init__(self, parent, callback):
        self.callback = callback

        top = self.top = tk.Toplevel(parent)
        label = tk.Label(top, text='Product name:')
        label.pack()

        self.product = tk.Entry(top)
        self.product.pack()

        label = tk.Label(top, text='Tracking Number:')
        label.pack()

        self.track = tk.Entry(top)
        self.track.pack()

        tk.Button(top, text='Save', command=self.send).pack()
        tk.Button(top, text='Close', command=self.close).pack()

        center(top)

    def close(self):
        self.top.destroy()

    def send(self):
        if self.product.get() and self.track.get():
            self.callback(self.product.get(), self.track.get())
            self.top.destroy()
        else:
            box.showerror("Error", "All field is required!")


class ChinaPostAirMail(tk.Tk):

    rowIndex = 0
    rows = []
    is_refreshing = False

    def _initDataBase(self):
        home = os.path.expanduser('~')
        self.db = shelve.open('%s/.air_mail.db' % home)

    def _createRow(self, data, j=0):
        row = []
        for j in range(len(data)):
            width = j == 2 and 50 or 20
            e = tk.Entry(self.fm, relief=tk.RIDGE, width=width, borderwidth=0)
            e.grid(row=self.rowIndex, column=j, sticky=tk.NSEW)
            e.insert(tk.END, data[j])
            row.append(e)
        tk.Button(
            self.fm, text='x', command=lambda: self.onDelete(data[1])).grid(
                row=self.rowIndex, column=(j + 1))
        self.rows.append(row)

        self.rowIndex += 1

    def _createTable(self):
        self.fm = tk.Frame(self, bg="white")
        self.fm.pack(side=tk.TOP, expand=tk.YES, fill=tk.NONE)
        keys = self.db.keys()
        keys.sort()
        for key in keys:
            if isinstance(self.db[key], list):
                self._createRow(self.db[key] + ['not sync'])

    def _addButtons(self):
        fm = tk.Frame(self, bg="white")
        fm.pack(side=tk.BOTTOM, expand=tk.YES, fill=tk.NONE)
        tk.Button(fm, text='Add', command=self.onAdd).grid(row=0, column=0)
        tk.Button(fm, text='Save', command=self.onSave).grid(row=0, column=1)
        tk.Button(fm, text='Refresh',
                  command=self.onRefresh).grid(row=0, column=2)
        tk.Button(fm, text='Settings',
                  command=self.onSettings).grid(row=0, column=3)
        tk.Button(fm, text='Clean', command=self.onClean).grid(row=0, column=4)
        tk.Button(fm, text='Close', command=self.onClose).grid(row=0, column=5)

    def _initStatusBar(self):
        label = tk.Label(text='Product')
        label.grid(row=0)

    def _addToDb(self, product, number):
        self._createRow([product, number, 'not sync'])
        self.db[number] = [product, number]
        self.db.sync()

    def _getText(self, element):
        return tools.text.normalize_space(tools.lxml_tools.get_node_text(
            element
        ))

    def __getCaptcha(self, image_file='/tmp/.air_mail.jpeg'):
        if hasattr(self, 'code'):
            return

        self.g.go('http://track-chinapost.com/startairmail.php')
        self.image = self.g.xpath('//img[@id="verifyimg"]').get('src')
        self.cookie = self.g.xpath('//input[@name="cookie"]').get('value')
        self.g.download(self.image, image_file)
        self.code = str(AntiGate(self.db['api_key'], image_file))

    def __getPage(self):
        self.g.setup(post={
            'code': self.code, 'num': self.number,
            'cookie': self.cookie, 'submit': ''
        })
        self.g.go('http://track-chinapost.com/track_chinapost.php')
        return self._getText(self.g.xpath('//div[@class="info"]/p'))

    def __getStatus(self):
        data = self.g.xpath_list('//table[@id="main_tab"]/tr')[-1]
        status = self._getText(data.xpath('td[3]')[0])
        date = self._getText(data.xpath('td[6]')[0])
        message = '%s / %s' % (status, date)
        if message == 'Status / Date':
            return 'no tracking info'
        return message

    def _getMailStatus(self):
        self.__getCaptcha()
        for i in range(3):
            info = self.__getPage()
            if 'verification code is wrong' in info:
                del self.code
                self.__getCaptcha()
                continue
            return self.__getStatus()
        return 'error'

    def _setMessage(self, e, message):
        e.delete(0, tk.END)
        e.insert(tk.END, message)

    def _onRefresh(self):
        for row in self.rows:
            self._setMessage(row[STATUS], 'updating ...')
            self.number = row[KEY].get()
            try:
                status = self._getMailStatus()
            except:
                status = 'can not get info'
            self._setMessage(row[STATUS], status)
            time.sleep(5)
        del self.code
        self.is_refreshing = False

    def onRefresh(self):
        if self.is_refreshing:
            box.showinfo("Information", "Is running ...")
            return
        elif 'api_key' not in self.db.keys():
            box.showerror("Error", "API key is not set!")
            return
        else:
            self.is_refreshing = True
            thread.start_new_thread(self._onRefresh, ())

    def onAdd(self):
        TrackAddDialog(self, self._addToDb)

    def onClose(self):
        self.destroy()

    def onDelete(self, key):
        del self.db[key]
        self.db.sync()
        for row in self.rows:
            if row[KEY].get() == key:
                for e in row:
                    e.grid_forget()

    def onClean(self):
        for row in self.rows:
            for e in row:
                e.grid_forget()
        self.db.clear()
        self.db.sync()

    def onSave(self):
        for row in self.rows:
            key = row[KEY].get()
            if key in self.db.keys():
                self.db[key] = [row[NAME].get(), key]
        self.db.sync()

    def _saveSettings(self, api_key):
        self.db['api_key'] = api_key
        self.db.sync()

    def onSettings(self):
        SettingsDialog(self, self._saveSettings, self.db.get('api_key', ''))

    def _initGrab(self, cookie_file='/tmp/.airmail.cookie'):
        self.g = Grab()
        self.g.setup(
            hammer_mode=True, hammer_timeouts=((60, 70), (80, 90), (100, 110)),
            reuse_cookies=True, cookiefile=cookie_file
        )
        open(cookie_file, 'w').close()

    def main(self):
        self.title('ChinaPost / AirMail tracking')
        self._initGrab()
        self._initDataBase()
        self._addButtons()
        self._createTable()
        center(self)
        self.mainloop()

    def __del__(self):
        self.db.sync()
        self.db.close()


def run():
    ui = ChinaPostAirMail()
    ui.main()


if __name__ == '__main__':
    run()
