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
Create cleaners from CleanerML (markup language)
"""

from __future__ import absolute_import, print_function

import bleachbit
from bleachbit.Action import ActionProvider
from bleachbit import _
from bleachbit.General import boolstr_to_bool, getText
from bleachbit.FileUtilities import expand_glob_join, listdir
from bleachbit import Cleaner

import logging
import os
import sys
import xml.dom.minidom
#모듈을 불러온다.

logger = logging.getLogger(__name__)
#logging모듈의 getLogger함수를 써서 __name__의 로거 추출


class CleanerML:

    """Create a cleaner from CleanerML"""

    def __init__(self, pathname, xlate_cb=None):
        """Create cleaner from XML in pathname.

        If xlate_cb is set, use it as a callback for each
        translate-able string.
        """

        self.action = None
        self.cleaner = Cleaner.Cleaner()
        self.option_id = None
        self.option_name = None
        self.option_description = None
        self.option_warning = None
        self.vars = {}
        self.xlate_cb = xlate_cb
        # action,cleaner,option_id,option_name,option_description,option_warning,vars,xlate_cb 메서드 값 초기화
        if self.xlate_cb is None:
            self.xlate_mode = False
            self.xlate_cb = lambda x, y=None: None  # do nothing
            #만약 xlate_cb 메서드 값이 None이면 xlate_mode는 false가 되고, xlate_cb는 x,y값이 None이면 None값을 돌려주는 함수가 된다.
        else:
            self.xlate_mode = True
            #xlate_cb가 None이 아니면 xlate_mode는 True가 된다.
        dom = xml.dom.minidom.parse(pathname)
        #xml형식으로된 pathname을 xml파싱이 가능한 형식으로 변형해서 dom에 저장
        self.handle_cleaner(dom.getElementsByTagName('cleaner')[0])
        # handle_cleaner함수에 cleaner태그의 첫번째 요소를 변수로 사용

    def get_cleaner(self):
        """Return the created cleaner"""
        return self.cleaner
        # CleanerML클래스의 cleaner 메서드 리턴

    def os_match(self, os_str, platform=sys.platform):
        """Return boolean whether operating system matches
           지원하는 운영체제와 일치하는지 Boolean값으로 리턴해주는 함수

        Keyword arguments:
        os_str -- the required operating system as written in XML XML형식으로 써진 운영체제
        platform -- used only for unit tests 시스템모듈로 추출한 platform을 저장하는 변수
        """
        # If blank or if in .pot-creation-mode, return true.
        if len(os_str) == 0 or self.xlate_mode:
            return True
            # XML형식으로 써진 운영체제이름을 저장한 변수 os_str이 비어있거나 xlate_mode가 True이면 return true

        # Otherwise, check platform. 다른 경우 플랫폼을 확인한다
        # Define the current operating system. 그리고 현재 운영체제를 정의한다.
        if platform == 'darwin':
            current_os = ('darwin', 'bsd', 'unix')
            # platform이 darwin일때 current_os(현재 운영체제) 정의
        elif platform.startswith('linux'):
            current_os = ('linux', 'unix')
            # platform이 linux일때 current_os(현재 운영체제) 정의
        elif platform.startswith('openbsd'):
            current_os = ('bsd', 'openbsd', 'unix')
            # platform이 openbsd일때 current_os(현재 운영체제) 정의
        elif platform.startswith('netbsd'):
            current_os = ('bsd', 'netbsd', 'unix')
            # platform이 netbsd일때 current_os(현재 운영체제) 정의
        elif platform.startswith('freebsd'):
            current_os = ('bsd', 'freebsd', 'unix')
            # platform이 freebsd일때 current_os(현재 운영체제) 정의
        elif platform == 'win32':
            current_os = ('windows')
            # platform이 win32일때 current_os(현재 운영체제) 정의
        else:
            raise RuntimeError('Unknown operating system: %s ' % sys.platform)
        # Compare current OS against required OS.
        # platform의 값이 해당되는 것이 없으면 알수없는 운영체제라는 런타임에러 메세지 출력
        return os_str in current_os
        # current_os에서 os_str 반환

    def handle_cleaner(self, cleaner):
        """<cleaner> element"""
        # cleaner태그 요소 정의

        if not self.os_match(cleaner.getAttribute('os')):
            return
            # cleaner객체에서 os속성을 가져와 os_match함수를 이용해 운영체제가 일치하는지 확인
            # 일치하지 않으면 return

        self.cleaner.id = cleaner.getAttribute('id')
        # cleaner에서 id속성 추출
        self.handle_cleaner_label(cleaner.getElementsByTagName('label')[0])
        # cleaner에서 label이라는 이름을 가진 태그의 첫번째요소를 변수로 handle_cleaner_label함수 호출
        description = cleaner.getElementsByTagName('description')
        # cleaner에서 description이라는 이름을 가진 태그들 추출
        if description and description[0].parentNode == cleaner:
            self.handle_cleaner_description(description[0])
            # description과 description의 첫번째요소의 부모노드가 cleaner일 경우
            # handle_cleaner_description함수에 description의 첫번째 요소를 넣어서 호출
            # cleaner태그 아래에 label태그가 없고 바로 description태그가 오는경우 description의 부모노드가 cleaner가 된다
            # 즉 cleaner태그 다음 description태그가 사용된 경우 이 함수를 사용한다.

        for var in cleaner.getElementsByTagName('var'):
            self.handle_cleaner_var(var)
            # cleaner의 var태그들을 반복해서 handle_cleaner_var 함수 호출
        for option in cleaner.getElementsByTagName('option'):
            # option태그들을 추출해서 반복

            try: # 예외처리부분
                self.handle_cleaner_option(option)
                # 추출한 option속성값으로 handle_cleaner_option함수 호출
            except:
                logger.exception('error in handle_cleaner_option() for cleaner id = %s, option XML=%s',
                                 self.cleaner.id, option.toxml())
                                 # 에러 발생시 에러가 발생한 부분 출력
        self.handle_cleaner_running(cleaner.getElementsByTagName('running'))
        # running태그를 추출하여 handle_cleaner_running함수 호출
        self.handle_localizations(
            cleaner.getElementsByTagName('localizations'))
            # localizations태그를 추출하여 handle_localizations 함수 호출

    def handle_cleaner_label(self, label):
        """<label> element under <cleaner>
           cleaner태그 아래에 label태그 요소"""

        self.cleaner.name = _(getText(label.childNodes))
        # label객체의 자식노드들을 text로 추출해서 self.cleaner.name에 저장
        translate = label.getAttribute('translate')
        #label에서 translate속성 추출
        if translate and boolstr_to_bool(translate):
            self.xlate_cb(self.cleaner.name)
            # translate 와 translate를 bool값으로 한것이 True면
            # xlate_cb함수에 self.cleaner.name값을 넣어서 사용
            """ xlate_cb함수가 번역과 관련된 함수인데 위에서 xlate_cb의 값이 None이면
                xlate_mode는 False이고이 함수는 None값을 돌려주는 함수가됨 """
            """ xlate_mode의 값이 None이 아니면 xlate_mode가 True가 되는것으로 보아
                xlate_mode가  True일땐 값을 번역하고 None일땐 번역하지 않는 기능을 하는것 같음. """

    def handle_cleaner_description(self, description):
        """<description> element under <cleaner>
            cleaner태그 아래에서 description태그 요소"""
        self.cleaner.description = _(getText(description.childNodes))
        # description의 자식노드들을 text로 추출하여 self.cleaner.description에 저장
        # 여기서 description의 자식노드란 <description>설명</description> 이 있을때 설명 부분에 해당한다.

        translators = description.getAttribute('translators')
        #description에서 translators속성 값을 추출
        self.xlate_cb(self.cleaner.description, translators)
        # xlate_cb함수를 사용

    def handle_cleaner_running(self, running_elements):
        """<running> element under <cleaner>
           cleaner태그 아래의 running태그 요소"""
        # example: <running type="command">opera</running>
        for running in running_elements: # running_elements의 요소를 running에 반복
            if not self.os_match(running.getAttribute('os')):
                continue
                # 만약 running에서 추출한 os(현재 사용중인 운영체제)가 지원하는 os와 일치하지않으면 continue
            detection_type = running.getAttribute('type')
            # running에서 type속성 값 추출 (실행 중인 프로그램의 type)
            value = getText(running.childNodes)
            # running의 자식노드들을 text로 추출
            self.cleaner.add_running(detection_type, value)
            # 추출한 실행 중인 프로그램의 type과 value로 add_running함수 사용
            # add_running은 현재 실행 중인 프로그램을 검색하는 방법을 추가하는 함수

    def handle_cleaner_option(self, option):
        """<option> element"""
        self.option_id = option.getAttribute('id')
        # option의 id속성 값 추출해서 저장
        self.option_description = None
        # option_description 선언
        self.option_name = None
        # option_name 선언

        self.handle_cleaner_option_label(
            option.getElementsByTagName('label')[0])
        description = option.getElementsByTagName('description')
        self.handle_cleaner_option_description(description[0])
        warning = option.getElementsByTagName('warning')
        if warning:
            self.handle_cleaner_option_warning(warning[0])
            if self.option_warning:
                self.cleaner.set_warning(self.option_id, self.option_warning)

        for action in option.getElementsByTagName('action'):
            self.handle_cleaner_option_action(action)

        self.cleaner.add_option(
            self.option_id, self.option_name, self.option_description)

    def handle_cleaner_option_label(self, label):
        """<label> element under <option>"""
        self.option_name = _(getText(label.childNodes))
        translate = label.getAttribute('translate')
        translators = label.getAttribute('translators')
        if not translate or boolstr_to_bool(translate):
            self.xlate_cb(self.option_name, translators)

    def handle_cleaner_option_description(self, description):
        """<description> element under <option>"""
        self.option_description = _(getText(description.childNodes))
        translators = description.getAttribute('translators')
        self.xlate_cb(self.option_description, translators)

    def handle_cleaner_option_warning(self, warning):
        """<warning> element under <option>"""
        self.option_warning = _(getText(warning.childNodes))
        self.xlate_cb(self.option_warning)

    def handle_cleaner_option_action(self, action_node):
        """<action> element under <option>"""
        if not self.os_match(action_node.getAttribute('os')):
            return
        command = action_node.getAttribute('command')
        provider = None
        for actionplugin in ActionProvider.plugins:
            if actionplugin.action_key == command:
                provider = actionplugin(action_node, self.vars)
        if provider is None:
            raise RuntimeError("Invalid command '%s'" % command)
        self.cleaner.add_action(self.option_id, provider)

    def handle_localizations(self, localization_nodes):
        """<localizations> element under <cleaner>"""
        if not 'posix' == os.name:
            return
        from bleachbit import Unix
        for localization_node in localization_nodes:
            for child_node in localization_node.childNodes:
                Unix.locales.add_xml(child_node)
        # Add a dummy action so the file isn't reported as unusable
        self.cleaner.add_action('localization', ActionProvider(None))

    def handle_cleaner_var(self, var):
        """Handle one <var> element under <cleaner>.

        Example:

        <var name="basepath">
         <value search="glob">~/.config/f*</value>
         <value>~/.config/foo</value>
         <value>%AppData\foo</value>
         </var>
        """
        var_name = var.getAttribute('name')
        for value_element in var.getElementsByTagName('value'):
            if not self.os_match(value_element.getAttribute('os')):
                continue
            value_str = getText(value_element.childNodes)
            is_glob = value_element.getAttribute('search') == 'glob'
            if is_glob:
                value_list = expand_glob_join(value_str, '')
            else:
                value_list = [value_str, ]
            if self.vars.has_key(var_name):
                # append
                self.vars[var_name] = value_list + self.vars[var_name]
            else:
                # initialize
                self.vars[var_name] = value_list


def list_cleanerml_files(local_only=False):
    """List CleanerML files"""
    cleanerdirs = (bleachbit.personal_cleaners_dir, )
    if bleachbit.local_cleaners_dir:
        # If the application is installed, locale_cleaners_dir is None
        cleanerdirs = (bleachbit.local_cleaners_dir, )
    if not local_only and bleachbit.system_cleaners_dir:
        cleanerdirs += (bleachbit.system_cleaners_dir, )
    for pathname in listdir(cleanerdirs):
        if not pathname.lower().endswith('.xml'):
            continue
        import stat
        st = os.stat(pathname)
        if sys.platform != 'win32' and stat.S_IMODE(st[stat.ST_MODE]) & 2:
            logger.warning("ignoring cleaner because it is world writable: %s", pathname)
            continue
        yield pathname


def load_cleaners():
    """Scan for CleanerML and load them"""
    for pathname in list_cleanerml_files():
        try:
            xmlcleaner = CleanerML(pathname)
        except:
            logger.exception('error reading cleaner: %s', pathname)
            continue
        cleaner = xmlcleaner.get_cleaner()
        if cleaner.is_usable():
            Cleaner.backends[cleaner.id] = cleaner
        else:
            logger.debug('cleaner is not usable on this OS because it has no actions: %s', pathname)


def pot_fragment(msgid, pathname, translators=None):
    """Create a string fragment for generating .pot files"""
    msgid = msgid.replace('"', '\\"') # escape quotation mark
    if translators:
        translators = "#. %s\n" % translators
    else:
        translators = ""
    ret = '''%s#: %s
msgid "%s"
msgstr ""

''' % (translators, pathname, msgid)
    return ret


def create_pot():
    """Create a .pot for translation using gettext"""

    f = open('../po/cleanerml.pot', 'w')

    for pathname in listdir('../cleaners'):
        if not pathname.lower().endswith(".xml"):
            continue
        strings = []
        try:
            CleanerML(pathname,
                      lambda newstr, translators=None:
                      strings.append([newstr, translators]))
        except:
            logger.exception('error reading: %s', pathname)
            continue
        for (string, translators) in strings:
            f.write(pot_fragment(string, pathname, translators))

    f.close()
