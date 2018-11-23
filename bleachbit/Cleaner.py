# vim: ts=4:sw=4:expandtab

# BleachBit
# Copyright (C) 2008-2018 Andrew Ziem
# https://www.bleachbit.org
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.


"""
Perform (or assist with) cleaning operations.
"""

#모듈을 불러온다.
from __future__ import absolute_import, print_function
"""absolute_import, print_function 모듈을 __future__로부터 불러온다."""
from bleachbit import _, expanduser, expandvars
""" _, expanduser, expandvars 모듈을 bleachbit로부터 불러온다."""
from bleachbit.FileUtilities import children_in_directory
"""children_in_directory 모듈을 bleachbit의 FileUtilities로부터 불러온다"""
from bleachbit.Options import options
"""options모듈을 bleachbit의 Options로부터 불러온다"""
from bleachbit import Command, FileUtilities, Memory, Special
"""Comman,FileUtilities,Memory,special 모듈을 bleachbit로부터 불러온다"""

import glob
import logging
import os.path
import re
import sys
import warnings
""" glob, logging, os.path, re, sys, warnings 모듈을 불러온다 """

if 'posix' == os.name:
    from bleachbit import Unix
    """ 만약 운영체제의 이름이 posix이면 bleachbit로부터 Unix모듈을 불러온다"""
elif 'nt' == os.name:
    from bleachbit import Windows
    """ 운영체제의 이름이 nt면 bleachbit로부터 Windows모듈을 불러온다"""

# Suppress GTK warning messages while running in CLI #34
warnings.simplefilter("ignore", Warning)
 """ warnigs모듈의 simplefilter함수를 사용해 간단한 경고 필터 설정"""


try:                       """예외처리"""
    import gtk
    HAVE_GTK = True
    """ gtk 모듈을 불러오고 HAVE_GTK의 값을 True로 한다"""
except ImportError:
    HAVE_GTK = False
    """ 모듈을 불러올때 에러 발생시 HAVE_GTK의 값을 False로 한다"""

# a module-level variable for holding cleaners
backends = {}


class Cleaner:

    """Base class for a cleaner"""           # cleaner의 기본 클래스
 
    def __init__(self):                      # 생성자
        self.actions = []                    # 메서드들을 초기화 및 생성
        self.id = None
        self.description = None
        self.name = None
        self.options = {}
        self.running = []
        self.warnings = {}
        self.regexes_compiled = []

    def add_action(self, option_id, action):
        """Register 'action' (instance of class Action) to be executed     # option_id에 대해 실행할 action을 등록하는함수
        for ''option_id'.  The actions must implement list_files and
        other_cleanup()"""  
        self.actions += ((option_id, action), )                          # cleaner의 action 메서드에 option_id와 action 추가

    def add_option(self, option_id, name, description):        
        """Register option (such as 'cache')"""              # cache와 같은 option을 등록하는 함수
        self.options[option_id] = (name, description)        # 키값이 option_id인 option딕셔너리의 밸류를 name,description로 저장

    def add_running(self, detection_type, pathname):
        """Add a way to detect this program is currently running"""    # 현재 실행중인 프로그램을 검색하는 방법을 추가하는 함수
        self.running += ((detection_type, pathname), )                # running 리스트에 detection_type, pathname 추가

    def auto_hide(self):
        """Return boolean whether it is OK to automatically hide this  #클리너를 자동으로 숨길지에 대한 여부를 boolean값으로 반환하는함수
        cleaner"""                           
        for (option_id, __name) in self.get_options():     # options딕셔너리의 값을 반복
            try:       #예외처리부분
                for cmd in self.get_commands(option_id): # option_id에서 명령인스턴스 목록을 가져와서 반복 
                    for dummy in cmd.execute(False):  
                        return False
                for ds in self.get_deep_scan(option_id):
                    if isinstance(ds, dict):
                        return False
            except Exception:
                logger = logging.getLogger(__name__) # __name__의 로거 추출
                logger.exception('exception in auto_hide(), cleaner=%s, option=%s',
                                 self.name, option_id) # 이 로거의 오류 레벨 메시지를 기록,
        return True

    def get_commands(self, option_id):
        """Get list of Command instances for option 'option_id'""" # 옵션option_id 에대한 명령 인스턴스 목록을 가져오는 함수.
        for action in self.actions: # actions리스트에 있는 값 반복
            if option_id == action[0]: # option_id의 값이 actions리스트의 있는 값의 첫번째요소 일경우
                for cmd in action[1].get_commands(): 
                    yield cmd                         # action[1]의 command를 추출해서 반복하고 return
        if option_id not in self.options:             # options 딕셔너리에 option_id가 없을경우
            raise RuntimeError("Unknown option '%s'" % option_id)  # 알수없는 option이라는 에러를 발생시킴

    def get_deep_scan(self, option_id):
        """Get dictionary used to build a deep scan"""  # 딥스캔을 빌드하기위해 사용된 딕셔너리를 가져오는 함수.
        for action in self.actions:  # actions의 리스트값 반복
            if option_id == action[0]: # 반복하는 값이 option_id와 일치하면 
                for ds in action[1].get_deep_scan(): # action[1]에서 딥스캔을 빌드하기위해 사용된 딕셔너리를 반복하고 return
                    yield ds 
                                                # add_action 함수에 의해 actions는 (option_id, action) 으로 구성된다.
                                                # 따라서 action[0] 는 add_action에 의해 추가된 option_id를 나타내고 action[1] = action
        if option_id not in self.options: # opntions 딕셔너리에 option_id가 없으면 
            raise RuntimeError("Unknown option '%s'" % option_id)   # 런타임에러 발생
 
    def get_description(self):
        """Brief description of the cleaner"""  # description(클리너에대한 간략한 설명)을 반환하는 함수
        return self.description

    def get_id(self):
        """Return the unique name of this cleaner"""  # 클리너의 고유 id를 반환하는 함수
        return self.id

    def get_name(self):
        """Return the human name of this cleaner""" # 이 클리너의 사용자 이름을 반환하는 함수
        return self.name

    def get_option_descriptions(self):
        """Yield the names and descriptions of each option in a 2-tuple""" # 각 옵션의 이름과 설명을 2-tuple로 yield 하는 함수
        if self.options:                         
            for key in sorted(self.options.keys()):             #options에 값이 있으면 options의 key를 정렬하여 반복
                yield (self.options[key][0], self.options[key][1]) # 옵션의 이름과 설명을 튜플로 리턴
                # add_option함수로 key = option_id ,options[key][0] = name, options[key][1] = description임을 알수있다.
                
                

    def get_options(self):
        """Return user-configurable options in 2-tuple (id, name)"""  # 사용자 구성 가능옵션 반환
        if self.options:
            for key in sorted(self.options.keys()):  # options가 있으면 options의 키를 정렬하여 반복
                yield (key, self.options[key][0])    # key (option_id)와 options[key][0] (name) 을 return

    def get_warning(self, option_id):             # 경고를 문자열로 반환하는 함수
        """Return a warning as string."""
        if option_id in self.warnings:       # 만약 option_id가 warnings 딕셔너리에 있으면 
            return self.warnings[option_id]  # warnings[option_id] 반환 
        else:
            return None    # 없으면 아무것도 반환하지 않음

    def is_running(self):
        """Return whether the program is currently running"""    # 프로그램이 현재 실행 중인지 여부를 반환하는 함수
        logger = logging.getLogger(__name__)            # __name__에서 로거 추출
        for running in self.running:           # running 리스트의 값들 반복      
            test = running[0]         # running[0] = detection_type   ( add_running 함수 참고)               
            pathname = running[1]             
            if 'exe' == test and 'posix' == os.name:  # os이름이 posix이고 exe 타입인지 확인
                if Unix.is_running(pathname): # Unix에서 is_running함수썼을때 True이면 
                    logger.debug("process '%s' is running", pathname) # 프로세스가 실행중이라는 debug 메세지를 로그하고 True반환
                    return True
            elif 'exe' == test and 'nt' == os.name: # os이름이 nt 이고 exe타입인지 확인
                if Windows.is_process_running(pathname):  # 만약 Windows에서 is_process_running 함수를 사용했을때 true이면
                    logger.debug("process '%s' is running", pathname) # 프로세스가 실행중이라는 debug 메세지를 로그하고 true반환
                    return True
            elif 'pathname' == test:                # test 
                expanded = expanduser(expandvars(pathname)) # pathname 안에 환경변수가 있으면 확장하고 현재 사용자 디렉토리의 절대경로로 대체
                                                            # ex) C:\\Documents and Settings\\Administrator\\pathname 
                for globbed in glob.iglob(expanded):  # iglob() : expanded의 모든 값을 실제로 동시에 저장하지 않고
                                                      #  glob()값과 동일한 값을 산출하는 반복기를 반환함
                    if os.path.exists(globbed): # globbed로 저장한 경로에 특정파일이 존재하는지 확인
                        logger.debug(
                            "file '%s' exists indicating '%s' is running", globbed, self.name)
                                # 존재하면 파일이 존재하며 실행중임을 나타내는 메세지출력
                        return True
            else:
                raise RuntimeError( 
                    "Unknown running-detection test '%s'" % test) # test가 exe , pathname도 아니면 알수없는 실행타입메세지와 함께 런타임에러발생
        return False

    def is_usable(self):
        """Return whether the cleaner is usable (has actions)""" # 클리너를 사용할 수 있는지 여부 반환
        return len(self.actions) > 0  # actions 리스트의 길이가 0보다 크다고 return

    def set_warning(self, option_id, description): 
        """Set a warning to be displayed when option is selected interactively"""
         # 옵션을 대화형으로 선택할 때 표시할 경고 설정
        self.warnings[option_id] = description
        # option_id에 대한 경고를 description으로 설정

class OpenOfficeOrg(Cleaner):

    """Delete OpenOffice.org cache"""

    def __init__(self):          # 생성자 
        Cleaner.__init__(self)  
        self.options = {} # OpenOfficeOrg의 options 딕셔너리 생성
        self.add_option('cache', _('Cache'), _('Delete the cache')) # option_id = cache, name = cache, description = delete the cache
        self.add_option('recent_documents', _('Most recently used'), _(  # option_id = recent_documents, name = Most recently
            "Delete the list of recently used documents"))               # description = delete the list of recently used documents
        self.id = 'openofficeorg'     #  사용자의 아이디 설정
        self.name = 'OpenOffice.org'  #  사용자의 이름 설정
        self.description = _("Office suite")  # 클래스의 설명 설정

        # reference: http://katana.oooninja.com/w/editions_of_openoffice.org
        if 'posix' == os.name:                                             # os가 posix인지 확인
            self.prefixes = ["~/.ooo-2.0", "~/.openoffice.org2",           # 
                             "~/.openoffice.org2.0", "~/.openoffice.org/3"]
            self.prefixes += ["~/.ooo-dev3"]
        if 'nt' == os.name:                                                # os가 nt인지 확인 ( nt = 윈도우 nt)
            self.prefixes = [
                "$APPDATA\\OpenOffice.org\\3", "$APPDATA\\OpenOffice.org2"]

    def get_commands(self, option_id):                                     
        # paths for which to run expand_glob_join
        egj = []    # expand_glob_join을 사용하기 위한 경로를 저장하는 용도
        if 'recent_documents' == option_id:       # option_id가 recent_documents(최근 문서) 이면
            egj.append(
                "user/registry/data/org/openoffice/Office/Histories.xcu") # egj에 경로를 추가
            egj.append(
                "user/registry/cache/org.openoffice.Office.Histories.dat") # egj에 경로를 추가

        if 'recent_documents' == option_id and not 'cache' == option_id:   # option_id가 recent_documents 이고 cache가 아니면
            egj.append("user/registry/cache/org.openoffice.Office.Common.dat")  # 다음 경로를 추가

        for egj_ in egj:    # egj에 들어있는 경로를 반복
            for prefix in self.prefixes:  # prefixes에 저장된 경로를 반복
                for path in FileUtilities.expand_glob_join(prefix, egj_): # prefix와 egj의 경로를 os형식에 맞게 연결하고
                                                                          # prefix와 egj의 경로에 환경변수가 있으면 확장한다음
                                                                          # 경로의 "~"을 사용자 디렉토리의 절대경로로 대체한다.
                                                    # 대체한 경로에 대응되는 모든 파일 및 디렉터리의 리스트를 이터레이터로 반환한 것을 반복
                    if 'nt' == os.name:                # os 이름 확인 
                        path = os.path.normpath(path)  # path의 경로를 정규화 ( 현재 디렉터리"."나 상위 디렉터리".."같은 구분자를 최대한 삭제)
                    if os.path.lexists(path):          # 경로의 파일이 존재하는지 확인
                        yield Command.Delete(path)     # 존재하면 삭제

        if 'cache' == option_id:
            dirs = []
            for prefix in self.prefixes:
                dirs += FileUtilities.expand_glob_join(
                    prefix, "user/registry/cache/")
            for dirname in dirs:
                if 'nt' == os.name:
                    dirname = os.path.normpath(dirname)
                for filename in children_in_directory(dirname, False):
                    yield Command.Delete(filename)

        if 'recent_documents' == option_id:
            for prefix in self.prefixes:
                for path in FileUtilities.expand_glob_join(prefix, "user/registry/data/org/openoffice/Office/Common.xcu"):
                    if os.path.lexists(path):
                        yield Command.Function(path,
                                               Special.delete_ooo_history,
                                               _('Delete the usage history'))
                # ~/.openoffice.org/3/user/registrymodifications.xcu
                #       Apache OpenOffice.org 3.4.1 from openoffice.org on Ubuntu 13.04
                # %AppData%\OpenOffice.org\3\user\registrymodifications.xcu
                # Apache OpenOffice.org 3.4.1 from openoffice.org on Windows XP
                for path in FileUtilities.expand_glob_join(prefix, "user/registrymodifications.xcu"):
                    if os.path.lexists(path):
                        yield Command.Function(path,
                                               Special.delete_office_registrymodifications,
                                               _('Delete the usage history'))


class System(Cleaner):

    """Clean the system in general"""

    def __init__(self):
        Cleaner.__init__(self)

        #
        # options for Linux and BSD
        #
        if 'posix' == os.name:
            # TRANSLATORS: desktop entries are .desktop files in Linux that
            # make up the application menu (the menu that shows BleachBit,
            # Firefox, and others.  The .desktop files also associate file
            # types, so clicking on an .html file in Nautilus brings up
            # Firefox.
            # More information:
            # http://standards.freedesktop.org/menu-spec/latest/index.html#introduction
            self.add_option('desktop_entry', _('Broken desktop files'), _(
                'Delete broken application menu entries and file associations'))
            self.add_option('cache', _('Cache'), _('Delete the cache'))
            # TRANSLATORS: Localizations are files supporting specific
            # languages, so applications appear in Spanish, etc.
            self.add_option('localizations', _('Localizations'), _(
                'Delete files for unwanted languages'))
            self.set_warning(
                'localizations', _("Configure this option in the preferences."))
            # TRANSLATORS: 'Rotated logs' refers to old system log files.
            # Linux systems often have a scheduled job to rotate the logs
            # which means compress all except the newest log and then delete
            # the oldest log.  You could translate this 'old logs.'
            self.add_option(
                'rotated_logs', _('Rotated logs'), _('Delete old system logs'))
            self.add_option('recent_documents', _('Recent documents list'), _(
                'Delete the list of recently used documents'))
            self.add_option('trash', _('Trash'), _('Empty the trash'))

        #
        # options just for Linux
        #
        if sys.platform.startswith('linux'):
            self.add_option('memory', _('Memory'),
                            # TRANSLATORS: 'free' means 'unallocated'
                            _('Wipe the swap and free memory'))
            self.set_warning(
                'memory', _('This option is experimental and may cause system problems.'))

        #
        # options just for Microsoft Windows
        #
        if 'nt' == os.name:
            self.add_option('logs', _('Logs'), _('Delete the logs'))
            self.add_option(
                'memory_dump', _('Memory dump'), _('Delete the file memory.dmp'))
            self.add_option('muicache', 'MUICache', _('Delete the cache'))
            # TRANSLATORS: Prefetch is Microsoft Windows jargon.
            self.add_option('prefetch', _('Prefetch'), _('Delete the cache'))
            self.add_option(
                'recycle_bin', _('Recycle bin'), _('Empty the recycle bin'))
            # TRANSLATORS: 'Update' is a noun, and 'Update uninstallers' is an option to delete
            # the uninstallers for software updates.
            self.add_option('updates', _('Update uninstallers'), _(
                'Delete uninstallers for Microsoft updates including hotfixes, service packs, and Internet Explorer updates'))

        #
        # options for GTK+
        #

        if HAVE_GTK:
            self.add_option('clipboard', _('Clipboard'), _(
                'The desktop environment\'s clipboard used for copy and paste operations'))

        #
        # options common to all platforms
        #
        # TRANSLATORS: "Custom" is an option allowing the user to specify which
        # files and folders will be erased.
        self.add_option('custom', _('Custom'), _(
            'Delete user-specified files and folders'))
        # TRANSLATORS: 'free' means 'unallocated'
        self.add_option('free_disk_space', _('Free disk space'),
                        # TRANSLATORS: 'free' means 'unallocated'
                        _('Overwrite free disk space to hide deleted files'))
        self.set_warning('free_disk_space', _('This option is very slow.'))
        self.add_option(
            'tmp', _('Temporary files'), _('Delete the temporary files'))

        self.description = _("The system in general")
        self.id = 'system'
        self.name = _("System")

    def get_commands(self, option_id):
        # cache
        if 'posix' == os.name and 'cache' == option_id:
            dirname = expanduser("~/.cache/")
            for filename in children_in_directory(dirname, True):
                if not self.whitelisted(filename):
                    yield Command.Delete(filename)

        # custom
        if 'custom' == option_id:
            for (c_type, c_path) in options.get_custom_paths():
                if 'file' == c_type:
                    yield Command.Delete(c_path)
                elif 'folder' == c_type:
                    yield Command.Delete(c_path)
                    for path in children_in_directory(c_path, True):
                        yield Command.Delete(path)
                else:
                    raise RuntimeError(
                        'custom folder has invalid type %s' % c_type)

        # menu
        menu_dirs = ['~/.local/share/applications',
                     '~/.config/autostart',
                     '~/.gnome/apps/',
                     '~/.gnome2/panel2.d/default/launchers',
                     '~/.gnome2/vfolders/applications/',
                     '~/.kde/share/apps/RecentDocuments/',
                     '~/.kde/share/mimelnk',
                     '~/.kde/share/mimelnk/application/ram.desktop',
                     '~/.kde2/share/mimelnk/application/',
                     '~/.kde2/share/applnk']

        if 'posix' == os.name and 'desktop_entry' == option_id:
            for dirname in menu_dirs:
                for filename in [fn for fn in children_in_directory(dirname, False)
                                 if fn.endswith('.desktop')]:
                    if Unix.is_broken_xdg_desktop(filename):
                        yield Command.Delete(filename)

        # unwanted locales
        if 'posix' == os.name and 'localizations' == option_id:
            for path in Unix.locales.localization_paths(locales_to_keep=options.get_languages()):
                if os.path.isdir(path):
                    for f in FileUtilities.children_in_directory(path, True):
                        yield Command.Delete(f)
                yield Command.Delete(path)

        # Windows logs
        if 'nt' == os.name and 'logs' == option_id:
            paths = (
                '$ALLUSERSPROFILE\\Application Data\\Microsoft\\Dr Watson\\*.log',
                '$ALLUSERSPROFILE\\Application Data\\Microsoft\\Dr Watson\\user.dmp',
                '$LocalAppData\\Microsoft\\Windows\\WER\\ReportArchive\\*\\*',
                '$LocalAppData\\Microsoft\\Windows\WER\\ReportQueue\\*\\*',
                '$programdata\\Microsoft\\Windows\\WER\\ReportArchive\\*\\*',
                '$programdata\\Microsoft\\Windows\\WER\\ReportQueue\\*\\*',
                '$localappdata\\Microsoft\\Internet Explorer\\brndlog.bak',
                '$localappdata\\Microsoft\\Internet Explorer\\brndlog.txt',
                '$windir\\*.log',
                '$windir\\imsins.BAK',
                '$windir\\OEWABLog.txt',
                '$windir\\SchedLgU.txt',
                '$windir\\ntbtlog.txt',
                '$windir\\setuplog.txt',
                '$windir\\REGLOCS.OLD',
                '$windir\\Debug\\*.log',
                '$windir\\Debug\\Setup\\UpdSh.log',
                '$windir\\Debug\\UserMode\\*.log',
                '$windir\\Debug\\UserMode\\ChkAcc.bak',
                '$windir\\Debug\\UserMode\\userenv.bak',
                '$windir\\Microsoft.NET\Framework\*\*.log',
                '$windir\\pchealth\\helpctr\\Logs\\hcupdate.log',
                '$windir\\security\\logs\\*.log',
                '$windir\\security\\logs\\*.old',
                '$windir\\SoftwareDistribution\\*.log',
                '$windir\\SoftwareDistribution\\DataStore\\Logs\\*',
                '$windir\\system32\\TZLog.log',
                '$windir\\system32\\config\\systemprofile\\Application Data\\Microsoft\\Internet Explorer\\brndlog.bak',
                '$windir\\system32\\config\\systemprofile\\Application Data\\Microsoft\\Internet Explorer\\brndlog.txt',
                '$windir\\system32\\LogFiles\\AIT\\AitEventLog.etl.???',
                '$windir\\system32\\LogFiles\\Firewall\\pfirewall.log*',
                '$windir\\system32\\LogFiles\\Scm\\SCM.EVM*',
                '$windir\\system32\\LogFiles\\WMI\\Terminal*.etl',
                '$windir\\system32\\LogFiles\\WMI\\RTBackup\EtwRT.*etl',
                '$windir\\system32\\wbem\\Logs\\*.lo_',
                '$windir\\system32\\wbem\\Logs\\*.log', )

            for path in paths:
                expanded = expandvars(path)
                for globbed in glob.iglob(expanded):
                    yield Command.Delete(globbed)

        # memory
        if sys.platform.startswith('linux') and 'memory' == option_id:
            yield Command.Function(None, Memory.wipe_memory, _('Memory'))

        # memory dump
        # how to manually create this file
        # http://www.pctools.com/guides/registry/detail/856/
        if 'nt' == os.name and 'memory_dump' == option_id:
            fname = expandvars('$windir\\memory.dmp')
            if os.path.exists(fname):
                yield Command.Delete(fname)
            for fname in glob.iglob(expandvars('$windir\\Minidump\\*.dmp')):
                yield Command.Delete(fname)

        # most recently used documents list
        if 'posix' == os.name and 'recent_documents' == option_id:
            ru_fn = expanduser("~/.recently-used")
            if os.path.lexists(ru_fn):
                yield Command.Delete(ru_fn)
            # GNOME 2.26 (as seen on Ubuntu 9.04) will retain the list
            # in memory if it is simply deleted, so it must be shredded
            # (or at least truncated).
            #
            # GNOME 2.28.1 (Ubuntu 9.10) and 2.30 (10.04) do not re-read
            # the file after truncation, but do re-read it after
            # shredding.
            #
            # https://bugzilla.gnome.org/show_bug.cgi?id=591404

            def gtk_purge_items():
                """Purge GTK items"""
                gtk.RecentManager().purge_items()
                yield 0

            for pathname in ["~/.recently-used.xbel", "~/.local/share/recently-used.xbel"]:
                pathname = expanduser(pathname)
                if os.path.lexists(pathname):
                    yield Command.Shred(pathname)
            if HAVE_GTK:
                # Use the Function to skip when in preview mode
                yield Command.Function(None, gtk_purge_items, _('Recent documents list'))

        if 'posix' == os.name and 'rotated_logs' == option_id:
            for path in Unix.rotated_logs():
                yield Command.Delete(path)

        # temporary files
        if 'posix' == os.name and 'tmp' == option_id:
            dirnames = ['/tmp', '/var/tmp']
            for dirname in dirnames:
                for path in children_in_directory(dirname, True):
                    is_open = FileUtilities.openfiles.is_open(path)
                    ok = not is_open and os.path.isfile(path) and \
                        not os.path.islink(path) and \
                        FileUtilities.ego_owner(path) and \
                        not self.whitelisted(path)
                    if ok:
                        yield Command.Delete(path)

        # temporary files
        if 'nt' == os.name and 'tmp' == option_id:
            dirname1 = expandvars(
                "$USERPROFILE\\Local Settings\\Temp\\")
            dirname2 = expandvars(r'%temp%')
            dirname3 = expandvars("%windir%\\temp\\")
            dirnames = []
            if Windows.get_windows_version() >= 6.0:
                # Windows Vista or later
                dirnames.append(dirname2)
            else:
                # Windows XP
                dirnames.append(dirname1)
            dirnames.append(dirname3)
            # whitelist the folder %TEMP%\Low but not its contents
            # https://bugs.launchpad.net/bleachbit/+bug/1421726
            for dirname in dirnames:
                low = os.path.join(dirname, 'low').lower()
                for filename in children_in_directory(dirname, True):
                    if not low == filename.lower():
                        yield Command.Delete(filename)

        # trash
        if 'posix' == os.name and 'trash' == option_id:
            dirname = expanduser("~/.Trash")
            for filename in children_in_directory(dirname, False):
                yield Command.Delete(filename)
            # fixme http://www.ramendik.ru/docs/trashspec.html
            # http://standards.freedesktop.org/basedir-spec/basedir-spec-0.6.html
            # ~/.local/share/Trash
            # * GNOME 2.22, Fedora 9
            # * KDE 4.1.3, Ubuntu 8.10
            dirname = expanduser("~/.local/share/Trash/files")
            for filename in children_in_directory(dirname, True):
                yield Command.Delete(filename)
            dirname = expanduser("~/.local/share/Trash/info")
            for filename in children_in_directory(dirname, True):
                yield Command.Delete(filename)
            dirname = expanduser("~/.local/share/Trash/expunged")
            # desrt@irc.gimpnet.org tells me that the trash
            # backend puts files in here temporary, but in some situations
            # the files are stuck.
            for filename in children_in_directory(dirname, True):
                yield Command.Delete(filename)

        # clipboard
        if HAVE_GTK and 'clipboard' == option_id:
            def clear_clipboard():
                gtk.gdk.threads_enter()
                clipboard = gtk.clipboard_get()
                clipboard.set_text("")
                gtk.gdk.threads_leave()
                return 0
            yield Command.Function(None, clear_clipboard, _('Clipboard'))

        # overwrite free space
        shred_drives = options.get_list('shred_drives')
        if 'free_disk_space' == option_id and shred_drives:
            for pathname in shred_drives:
                # TRANSLATORS: 'Free' means 'unallocated.'
                # %s expands to a path such as C:\ or /tmp/
                display = _("Overwrite free disk space %s") % pathname

                def wipe_path_func():
                    for ret in FileUtilities.wipe_path(pathname, idle=True):
                        # Yield control to GTK idle because this process
                        # is very slow.  Also display progress.
                        yield ret
                    yield 0
                yield Command.Function(None, wipe_path_func, display)

        # MUICache
        if 'nt' == os.name and 'muicache' == option_id:
            keys = (
                'HKCU\\Software\\Microsoft\\Windows\\ShellNoRoam\\MUICache',
                'HKCU\\Software\\Classes\\Local Settings\\Software\\Microsoft\\Windows\\Shell\\MuiCache')
            for key in keys:
                yield Command.Winreg(key, None)

        # prefetch
        if 'nt' == os.name and 'prefetch' == option_id:
            for path in glob.iglob(expandvars('$windir\\Prefetch\\*.pf')):
                yield Command.Delete(path)

        # recycle bin
        if 'nt' == os.name and 'recycle_bin' == option_id:
            # This method allows shredding
            recycled_any = False
            for path in Windows.get_recycle_bin():
                recycled_any = True
                yield Command.Delete(path)
            # If there were any files deleted, Windows XP will show the
            # wrong icon for the recycle bin indicating it is not empty.
            # The icon will be incorrect until logging in to Windows again
            # or until it is emptied using the Windows API call for emptying
            # the recycle bin.

            # Windows 10 refreshes the recycle bin icon when the user
            # opens the recycle bin folder.

            # This is a hack to refresh the icon.
            def empty_recycle_bin_func():
                import tempfile
                tmpdir = tempfile.mkdtemp()
                Windows.move_to_recycle_bin(tmpdir)
                try:
                    Windows.empty_recycle_bin(None, True)
                except:
                    logging.getLogger(__name__).info('error in empty_recycle_bin()', exc_info=True)
                yield 0
            # Using the Function Command prevents emptying the recycle bin
            # when in preview mode.
            if recycled_any:
                yield Command.Function(None, empty_recycle_bin_func, _('Empty the recycle bin'))

        # Windows Updates
        if 'nt' == os.name and 'updates' == option_id:
            for wu in Windows.delete_updates():
                yield wu

    def init_whitelist(self):
        """Initialize the whitelist only once for performance"""
        regexes = [
            '^/tmp/.X0-lock$',
            '^/tmp/.truecrypt_aux_mnt.*/(control|volume)$',
            '^/tmp/.vbox-[^/]+-ipc/lock$',
            '^/tmp/.wine-[0-9]+/server-.*/lock$',
            '^/tmp/gconfd-[^/]+/lock/ior$',
            '^/tmp/fsa/',  # fsarchiver
            '^/tmp/kde-',
            '^/tmp/kdesudo-',
            '^/tmp/ksocket-',
            '^/tmp/orbit-[^/]+/bonobo-activation-register[a-z0-9-]*.lock$',
            '^/tmp/orbit-[^/]+/bonobo-activation-server-[a-z0-9-]*ior$',
            '^/tmp/pulse-[^/]+/pid$',
            '^/var/tmp/kdecache-',
            '^' + expanduser('~/.cache/wallpaper/'),
            # Clean Firefox cache from Firefox cleaner (LP#1295826)
            '^' + expanduser('~/.cache/mozilla'),
            # Clean Google Chrome cache from Google Chrome cleaner (LP#656104)
            '^' + expanduser('~/.cache/google-chrome'),
            '^' + expanduser('~/.cache/gnome-control-center/'),
            # iBus Pinyin
            # https://bugs.launchpad.net/bleachbit/+bug/1538919
            '^' + expanduser('~/.cache/ibus/'),
            # Linux Bluetooth daemon obexd
            '^' + expanduser('~/.cache/obexd/')]
        for regex in regexes:
            self.regexes_compiled.append(re.compile(regex))

    def whitelisted(self, pathname):
        """Return boolean whether file is whitelisted"""
        if not self.regexes_compiled:
            self.init_whitelist()
        for regex in self.regexes_compiled:
            if regex.match(pathname) is not None:
                return True
        return False


def register_cleaners():
    """Register all known cleaners: system, CleanerML, and Winapp2"""
    global backends

    # wipe out any registrations
    # Because this is a global variable, cannot use backends = {}
    backends.clear()

    # initialize "hard coded" (non-CleanerML) backends
    backends["openofficeorg"] = OpenOfficeOrg()
    backends["system"] = System()

    # register CleanerML cleaners
    from bleachbit import CleanerML
    CleanerML.load_cleaners()

    # register Winapp2.ini cleaners
    if 'nt' == os.name:
        from bleachbit import Winapp
        Winapp.load_cleaners()


def create_simple_cleaner(paths):
    """Shred arbitrary files (used in CLI and GUI)"""
    cleaner = Cleaner()
    cleaner.add_option(option_id='files', name='', description='')
    cleaner.name = _("System")  # shows up in progress bar

    from bleachbit import Action

    class CustomFileAction(Action.ActionProvider):
        action_key = '__customfileaction'

        def get_commands(self):
            for path in paths:
                if not isinstance(path, (str, unicode)):
                    raise RuntimeError(
                        'expected path as string but got %s' % str(path))
                if not os.path.isabs(path):
                    path = os.path.abspath(path)
                if os.path.isdir(path):
                    for child in children_in_directory(path, True):
                        yield Command.Shred(child)
                    yield Command.Shred(path)
                else:
                    yield Command.Shred(path)
    provider = CustomFileAction(None)
    cleaner.add_action('files', provider)
    return cleaner


def create_wipe_cleaner(path):
    """Wipe free disk space of arbitrary paths (used in GUI)"""
    cleaner = Cleaner()
    cleaner.add_option(
        option_id='free_disk_space', name='', description='')
    cleaner.name = ''

    # create a temporary cleaner object
    display = _("Overwrite free disk space %s") % path

    def wipe_path_func():
        for ret in FileUtilities.wipe_path(path, idle=True):
            yield ret
        yield 0

    from bleachbit import Action

    class CustomWipeAction(Action.ActionProvider):
        action_key = '__customwipeaction'

        def get_commands(self):
            yield Command.Function(None, wipe_path_func, display)
    provider = CustomWipeAction(None)
    cleaner.add_action('free_disk_space', provider)
    return cleaner
