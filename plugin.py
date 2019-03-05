import time
import os
import errno
import enigma
import log
import urllib
from enigma import eTimer
from Components.config import config, ConfigEnableDisable, ConfigSubsection, ConfigYesNo, ConfigClock, getConfigListEntry, ConfigText, ConfigSelection, ConfigNumber, ConfigSubDict, NoSave, ConfigPassword, ConfigSelectionNumber
from Screens.MessageBox import MessageBox
from Screens.Screen import Screen
from Screens.ChoiceBox import ChoiceBox
from Components.ConfigList import ConfigListScreen
from Components.ActionMap import ActionMap
from Components.Button import Button
from Components.Label import Label
from Components.SelectionList import SelectionList, SelectionEntryComponent
from Components.ScrollLabel import ScrollLabel
import Components.PluginComponent
from Plugins.Plugin import PluginDescriptor
from twisted.internet import reactor, threads
from xml.etree.cElementTree import fromstring, ElementTree
try:
    from urllib.request import urlopen, URLError
except ImportError:
    from urllib2 import Request, urlopen, URLError
import shutil
autoStartTimer = None
_session = None
IPv4 = None
debug = 0
version = '0.13'
config.plugins.duckdns = ConfigSubsection()
config.plugins.duckdns.enable = ConfigYesNo(default=False)
config.plugins.duckdns.updateinterval = ConfigSelectionNumber(default=15, min=5, max=180, stepwidth=5)
config.plugins.duckdns.hostname = ConfigText(default='', fixed_size=False)
config.plugins.duckdns.morehostname = ConfigYesNo(default=False)
config.plugins.duckdns.hostname2 = ConfigText(default='', fixed_size=False)
config.plugins.duckdns.hostname3 = ConfigText(default='', fixed_size=False)
config.plugins.duckdns.hostname4 = ConfigText(default='', fixed_size=False)
config.plugins.duckdns.hostname5 = ConfigText(default='', fixed_size=False)
config.plugins.duckdns.token = ConfigText(default='', fixed_size=False)
config.plugins.duckdns.usexml = ConfigYesNo(default=False)
config.plugins.duckdns.last_ip = ConfigText()
config.plugins.duckdns.pushoverenable = ConfigYesNo(default=False)
config.plugins.duckdns.apitoken = ConfigText(default='', fixed_size=False)
config.plugins.duckdns.userkey = ConfigText(default='', fixed_size=False)



class duckdnsConfig(ConfigListScreen, Screen):
    skin = '\n    <screen position="center,center" size="600,460" title="DuckDNS Updater"  >    \n       <ePixmap pixmap="skin_default/buttons/red.png" position="0,0" size="140,40" transparent="1" alphatest="on" />\n    <ePixmap pixmap="skin_default/buttons/green.png" position="140,0" size="140,40" transparent="1" alphatest="on" />\n    <ePixmap pixmap="skin_default/buttons/yellow.png" position="280,0" size="140,40" transparent="1" alphatest="on" />\n    <ePixmap pixmap="skin_default/buttons/blue.png" position="420,0" size="140,40" transparent="1" alphatest="on" />\n    <widget name="key_red" position="0,0" size="140,40" valign="center" halign="center" zPosition="4"  foregroundColor="white" font="Regular;20" transparent="1" shadowColor="background" shadowOffset="-2,-2" />\n    <widget name="key_green" position="140,0" size="140,40" valign="center" halign="center" zPosition="4"  foregroundColor="white" font="Regular;20" transparent="1" shadowColor="background" shadowOffset="-2,-2" />\n    <widget name="key_yellow" position="280,0" size="140,40" valign="center" halign="center" zPosition="4"  foregroundColor="white" font="Regular;20" transparent="1" shadowColor="background" shadowOffset="-2,-2" />\n    <widget name="key_blue" position="420,0" size="140,40" valign="center" halign="center" zPosition="4"  foregroundColor="white" font="Regular;20" transparent="1" shadowColor="background" shadowOffset="-2,-2" />\n    <ePixmap position="562,30" size="35,25" pixmap="skin_default/buttons/key_menu.png" alphatest="on" />\n    <widget name="config" position="10,60" size="590,450" scrollbarMode="showOnDemand" />\n  <widget name="statusbar" position="10,410" size="500,20" font="Regular;18" /> \n <widget name="upgradeinfo" position="10,430" size="565,20" font="Bold;18" />\n\t\t\t\t </screen>'

    def __init__(self, session, args = None):
        self.session = session
        Screen.__init__(self, session)
        self['pagetitle'] = Label(_('DuckDNS Menu'))
        self['key_red'] = Button(_('Exit'))
        self['key_green'] = Button(_('Save'))
        self['upgradeinfo'] = Label()
        self['setupActions'] = ActionMap(['SetupActions',
         'OkCancelActions',
         'ColorActions',
         'TimerEditActions',
         'MovieSelectionActions'], {'red': self.exit,
         'green': self.key_green,
         'cancel': self.exit,
         'contextMenu': self.openMenu}, -1)
        self['statusbar'] = Label()
        ConfigListScreen.__init__(self, [], session=self.session)
        self.XMLinfo()
        self.init_config()
        self.create_setup()
        self.showip()

    def init_config(self):

        def get_prev_values(section):
            res = {}
            for key, val in section.content.items.items():
                if isinstance(val, ConfigSubsection):
                    res[key] = get_prev_values(val)
                else:
                    res[key] = val.value

            return res

        self.duckdns = config.plugins.duckdns
        self.prev_values = get_prev_values(self.duckdns)
        self.cfg_enable = getConfigListEntry('Enable DuckDNS Updater:', self.duckdns.enable)
        self.cfg_updateinterval = getConfigListEntry('Update interval (Minutes):', self.duckdns.updateinterval)
        self.cfg_hostname = getConfigListEntry('DuckDNS Hostname:', self.duckdns.hostname)
        self.cfg_hostnameexplain = getConfigListEntry('The Below will update hostnames mentioned to the same ip')
        self.cfg_morehostname = getConfigListEntry('Using More Than One Hostname?:', self.duckdns.morehostname)
        self.cfg_hostname2 = getConfigListEntry('DuckDNS Hostname No.2:', self.duckdns.hostname2)
        self.cfg_hostname3 = getConfigListEntry('DuckDNS Hostname No.3:', self.duckdns.hostname3)
        self.cfg_hostname4 = getConfigListEntry('DuckDNS Hostname No.4:', self.duckdns.hostname4)
        self.cfg_hostname5 = getConfigListEntry('DuckDNS Hostname No.5:', self.duckdns.hostname5)
        self.cfg_token = getConfigListEntry('DuckDNS token:', self.duckdns.token)
        self.cfg_usexml = getConfigListEntry('Use Config XML File?', self.duckdns.usexml)
        self.cfg_pushoverenable = getConfigListEntry('Enable Pushover Update:', self.duckdns.pushoverenable)
        self.cfg_apitoken = getConfigListEntry('Pushover API Token:', self.duckdns.apitoken)
        self.cfg_userkey = getConfigListEntry('Pushover User Key:', self.duckdns.userkey)

    def create_setup(self):
        list = [self.cfg_enable]
        if self.duckdns.enable.value:
            list.append(self.cfg_updateinterval)
            list.append(self.cfg_hostname)
            list.append(self.cfg_token)
            list.append(self.cfg_usexml)
            list.append(self.cfg_morehostname)           
            if self.duckdns.morehostname.value:
                list.append(self.cfg_hostname2)
                list.append(self.cfg_hostname3)
                list.append(self.cfg_hostname4)
                list.append(self.cfg_hostname5)
            list.append(self.cfg_pushoverenable)
            if self.duckdns.pushoverenable.value:
                list.append(self.cfg_apitoken)
                list.append(self.cfg_userkey)           

        self['config'].list = list
        self['config'].l.setList(list)

    def new_config(self):
        cur = self['config'].getCurrent()
        if cur in (self.cfg_enable, self.cfg_updateinterval):
            self.create_setup()
        if cur in (self.cfg_enable, self.cfg_morehostname):
            self.create_setup()
        if cur in (self.cfg_enable, self.cfg_pushoverenable):
            self.create_setup()

    def keyLeft(self):
        ConfigListScreen.keyLeft(self)
        self.new_config()

    def keyRight(self):
        ConfigListScreen.keyRight(self)
        self.new_config()

    def key_green(self):
        for x in self['config'].list:
            x[1].save()

        self.close()

    def exit(self):
        print self['config'].list
        for x in self['config'].list:
            x[1].cancel()

        self.close()

    def openMenu(self):
        menu = [(_('Show log'), self.showLog),(_('Change Log'), self.changelog)]
        text = _('Select action')

        def setAction(choice):
            if choice:
                choice[1]()

        self.session.openWithCallback(setAction, ChoiceBox, title=text, list=menu)

    def XMLinfo(self):
        global hostname2
        global hostname3
        global hostname4
        global hostname5
        global hostname
        global token
        global apitoken
        global userkey
        if config.plugins.duckdns.usexml.value:
            try:
                with open('/etc/enigma2/DuckDNSUpdater/duckdns.xml') as file:
                    tree = ElementTree()
                    xml = tree.parse('/etc/enigma2/DuckDNSUpdater/duckdns.xml')
                    token = xml.findtext('token')
                    hostname = xml.findtext('hostname')
                    hostname2 = xml.findtext('hostname2')
                    hostname3 = xml.findtext('hostname3')
                    hostname4 = xml.findtext('hostname4')
                    hostname5 = xml.findtext('hostname5')
                    apitoken = xml.findtext('apitoken')                    
                    userkey = xml.findtext('userkey')
                    if config.plugins.duckdns.usexml.value:
                        config.plugins.duckdns.token.value = token
                        config.plugins.duckdns.hostname.value = hostname
                        config.plugins.duckdns.hostname2.value = hostname2
                        config.plugins.duckdns.hostname3.value = hostname3
                        config.plugins.duckdns.hostname4.value = hostname4
                        config.plugins.duckdns.hostname5.value = hostname5
                        config.plugins.duckdns.apitoken.value = apitoken
                        config.plugins.duckdns.userkey.value = userkey
                    else:
                        print >> log, ' [DUCKDNS] Config File is not in use'
            except IOError as e:
                print >> log, "[DUCKDNS] Config File couldn't be read"        

    def showLog(self):
        self.session.open(DuckDNSLog)

    def changelog(self):
        change = '\n V0.12: \n Added check to identify if the IP address has changed \n Added Debug for testing \n Added Changelog screen \n Added Current / Last IP update meaning no need to run after reboot \n V0.11: \n Inital Release \n V0.1: \n Creation of Plugin  '
        self.session.open(MessageBox, change, type=MessageBox.TYPE_INFO)
        
    def showip(self):
        if config.plugins.duckdns.last_ip:
            self['statusbar'].setText('Currently or Last Registered IP: {}'.format(config.plugins.duckdns.last_ip.value))        


class DuckDNSLog(Screen):
    skin = '\n    <screen position="center,center" size="560,400" title="DuckDNS Plugin Log" >\n     <ePixmap name="red" position="0,0" zPosition="2" size="140,40" pixmap="skin_default/buttons/red.png" transparent="1" alphatest="on" />\n    <ePixmap name="green" position="140,0" zPosition="2" size="140,40" pixmap="skin_default/buttons/green.png" transparent="1" alphatest="on" />\n    <ePixmap name="yellow" position="280,0" zPosition="2" size="140,40" pixmap="skin_default/buttons/yellow.png" transparent="1" alphatest="on" />\n    <ePixmap name="blue" position="420,0" zPosition="2" size="140,40" pixmap="skin_default/buttons/blue.png" transparent="1" alphatest="on" />\n    <widget name="key_red" position="0,0" size="140,40" valign="center" halign="center" zPosition="4" foregroundColor="white" font="Regular;20" transparent="1" shadowColor="background" shadowOffset="-2,-2" />\n    <widget name="key_green" position="140,0" size="140,40" valign="center" halign="center" zPosition="4" foregroundColor="white" font="Regular;20" transparent="1" shadowColor="background" shadowOffset="-2,-2" />\n    <widget name="key_yellow" position="280,0" size="140,40" valign="center" halign="center" zPosition="4" foregroundColor="white" font="Regular;20" transparent="1" shadowColor="background" shadowOffset="-2,-2" />\n    <widget name="key_blue" position="420,0" size="140,40" valign="center" halign="center" zPosition="4" foregroundColor="white" font="Regular;20" transparent="1" shadowColor="background" shadowOffset="-2,-2" />    \n    <widget name="list" position="10,40" size="540,340" />\n    </screen>'

    def __init__(self, session):
        self.session = session
        Screen.__init__(self, session)
        self['key_red'] = Button(_('Clear'))
        self['key_green'] = Button()
        self['key_yellow'] = Button()
        self['key_blue'] = Button()
        self['list'] = ScrollLabel(log.getvalue())
        self['actions'] = ActionMap(['DirectionActions',
         'OkCancelActions',
         'ColorActions',
         'MenuActions'], {'red': self.clear,
         'green': self.cancel,
         'yellow': self.cancel,
         'blue': self.cancel,
         'cancel': self.cancel,
         'ok': self.cancel,
         'left': self['list'].pageUp,
         'right': self['list'].pageDown,
         'up': self['list'].pageUp,
         'down': self['list'].pageDown,
         'pageUp': self['list'].pageUp,
         'pageDown': self['list'].pageDown,
         'menu': self.cancel}, -2)

    def cancel(self):
        self.close(False)

    def clear(self):
        log.logfile.reset()
        log.logfile.truncate()
        self.close(False)


class AppUrlOpener(urllib.FancyURLopener):
    version = 'Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/60.0.3112.113 Safari/537.36'


class AutoStartTimer:

    def __init__(self, session):
        self.session = session
        self.timer = eTimer()
        self.timer.callback.append(self.on_timer)
        self.update()

    def get_wake_time(self):
        if debug == 1:
            print >> log, '[DUCKDNS] AutoStartTimer -> get_wake_time'
        interval = int(config.plugins.duckdns.updateinterval.value)
        nowt = time.time()
        return int(nowt) + interval * 60

    def update(self):
        if debug == 1:
            print >> log, '[DUCKDNS] AutoStartTimer -> update'
        self.timer.stop()
        wake = self.get_wake_time()
        nowt = time.time()
        now = int(nowt)
        if wake > 0:
            if wake <= now:
                interval = int(config.plugins.duckdns.updateinterval.value)
                wake += interval * 60
            next_wake = wake - now
            self.timer.startLongTimer(next_wake)
        else:
            wake = -1
        print >> log, '[DUCKDNS] next wake up time {} (now={})'.format(time.asctime(time.localtime(wake)), time.asctime(time.localtime(now)))
        global debug
        debug = 0
        return wake

    def on_timer(self):
        self.timer.stop()
        now = int(time.time())
        wake = now
        print >> log, '[DUCKDNS] Timer Run {}'.format(time.asctime(time.localtime(now)))
        if wake - now < 60:
            try:
                start_update()
            except Exception as e:
                print >> log, '[DUCKDNS] on_timer Error:', e

        self.update()

    def get_status(self):
        if debug == 1:
            print >> log, '[DUCKDNS] AutoStartTimer -> getStatus'


def autostart(reason, session = None, **kwargs):
    global autoStartTimer
    global _session
    urllib._urlopener = AppUrlOpener()
    if debug == 1:
        print >> log, '[DUCKDNS] autostart {} occured at {}'.format(reason, time.time())
    if reason == 0 and _session is None:
        if session is not None:
            _session = session
            if autoStartTimer is None:
                autoStartTimer = AutoStartTimer(session)
    else:
        print >> log, '[DUCKDNS] stop'
    return


def get_next_wakeup():
    if debug == 1:
        print >> log, '[DUCKDNS] get_next_wakeup'
    return -1


def start_update():
    if config.plugins.duckdns.enable.value == True:
        global IPv4
        global debug
        IPv4 = config.plugins.duckdns.last_ip.value
        ''' The following is for debug & Testing IP Changes without them changing'''
        PATH='/usr/lib/enigma2/python/Plugins/Extensions/DuckDNSUpdater/debug.txt'
        if os.path.isfile(PATH) and os.access(PATH, os.R_OK):
            with open('/usr/lib/enigma2/python/Plugins/Extensions/DuckDNSUpdater/debug.txt', 'r') as myfile:
                text = myfile.read().decode('UTF-8').strip()
                IPv4 = text
                debug = 1
                print >> log, '[DUCKDNS] IP Debug Override Activated'
        ''' end of debug section '''
        url = 'http://myexternalip.com/raw'
        ip = urlopen(url).read().decode('utf-8')
        ''' The following is for debug & Testing IP Changes without them changing'''
        if debug == 1:
            print >> log, '[DUCKDNS] check IP ({}) IPV4 {}'.format(ip, IPv4)
            ''' end of debug section '''
        if ip == IPv4:
            print >> log, '[DUCKDNS] IP Status Unchanged ({})'.format(IPv4)
        else:
            nowt = time.time()
            now = int(nowt)
            print >> log, '[DUCKDNS] Update Started at ({})'.format(time.asctime(time.localtime(now)))
            hostname = config.plugins.duckdns.hostname.value
            token = config.plugins.duckdns.token.value
            if config.plugins.duckdns.morehostname.value:
                domains = '{0},{1},{2},{3},{4}'.format(config.plugins.duckdns.hostname.value, config.plugins.duckdns.hostname2.value, config.plugins.duckdns.hostname3.value, config.plugins.duckdns.hostname4.value, config.plugins.duckdns.hostname4.value)
                url = 'https://www.duckdns.org/update?domains={0}&token={1}&verbose=true'.format(domains, token)
            else:
                url = 'https://www.duckdns.org/update?domains={0}&token={1}&verbose=true'.format(hostname, token)
            updatetext = urlopen(url).read().decode('UTF-8').strip()
            updatestatus, IPv4, IPv6, changestatus = updatetext.split('\n')
            print >> log, '[DUCKDNS] OK = Good) (KO = Failed): Status ({})'.format(updatestatus)
            print >> log, '[DUCKDNS] Updated IPv4 IP Address If used: {}'.format(IPv4)
            print >> log, '[DUCKDNS] Updated IPv6 IP Address If used: {}'.format(IPv6)
            print >> log, '[DUCKDNS] [Update Status] IP Address ({})'.format(changestatus)
            print >> log, '[DUCKDNS] Update Finished at ({})'.format(time.asctime(time.localtime(now)))
            config.plugins.duckdns.last_ip.value = IPv4
            config.plugins.duckdns.last_ip.save()
            if config.plugins.duckdns.pushoverenable.value:
                message = 'Your IP address has now changed: New IP Address = {}'.format(IPv4)
                api = config.plugins.duckdns.apitoken.value
                userkey =  config.plugins.duckdns.userkey.value
                import httplib, urllib
                conn = httplib.HTTPSConnection("api.pushover.net:443")
                conn.request("POST", "/1/messages.json",
                  urllib.urlencode({
                    "token": api,
                    "user": userkey,
                    "message": message,
                  }), { "Content-type": "application/x-www-form-urlencoded" })
                conn.getresponse()
    else:
        print >> log, '[DUCKDNS] Updates are not enabled'




def main(session, **kwargs):
    session.openWithCallback(done_configuring, duckdnsConfig)


def done_configuring():
    print >> log, '[DUCKDNS] CHECKED FOR NEW VALUES (Done Configuring)'
    if autoStartTimer is not None:
        autoStartTimer.update()
    return


def Plugins(**kwargs):
    name = 'DuckDNS Updater'
    description = 'Plugin to Automatically Update DUCKDNS with your IP'
    result = [PluginDescriptor(name=name, description=description, where=[PluginDescriptor.WHERE_AUTOSTART, PluginDescriptor.WHERE_SESSIONSTART], fnc=autostart, wakeupfnc=get_next_wakeup), PluginDescriptor(name=name, description=description, where=[PluginDescriptor.WHERE_PLUGINMENU, PluginDescriptor.WHERE_EXTENSIONSMENU], icon='Duck-DNS-Logo.png', fnc=main)]
    return result