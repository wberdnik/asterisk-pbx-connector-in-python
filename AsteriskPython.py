#!/usr/bin/python3
# -*- coding: utf-8 -*-
version = '0.0.1'

import os
import argparse
import sys; sys.path.insert(0, sys.path[0]+'/tele')
from launcher import Launcher
 
# проверить ключи командной строки
# --help  список и расшифровка ключей
# migrate - создание таблиц БД
# trunk имя_транка - отдать нагрузку на транк
# call номер 9 цифр - тестовый звонок
# fixbd - обслуживание БД (упущенные номера и т.п)
# leadinka http сеанс с leadinka

 
def createParser ():
    # Создаем класс парсера
    parser = argparse.ArgumentParser(
            prog = 'TeleAsterisk',
            description = '''Программа обслуживания Asterisk''',
            epilog = '''(c) VLF 2020''',
            add_help = False
            )
    parent_group = parser.add_argument_group (title='Параметры')
    parent_group.add_argument ('--help', '-h', action='help', help='Справка')
    parent_group.add_argument ('--version', '-v', action='version',
            help = 'Вывести номер версии',
            version='%(prog)s {}'.format (version))

    subparsers = parser.add_subparsers (dest = 'command',
            title = 'Возможные команды',
            description = 'Команды, которые должны быть в качестве первого параметра %(prog)s')
 
    # Создаем migrate 
    migrate_parser = subparsers.add_parser ('migrate', 
            add_help = False,
            help = 'Добавление таблиц в MySQL',
            description = '''Добавление таблиц в MySQL при первичной инициализации''')

    migrate_parser.add_argument ('--help', '-h', action='help', help='Справка')
 
    # Создаем fixdb 
    fixdb_parser = subparsers.add_parser ('fixdb', 
            add_help = False,
            help = 'Регламентное обслуживание таблиц в MySQL',
            description = '''Регламентное обслуживание таблиц MySQL - подвисшие номера в БД, неверные статусы и т.п.''')
     
    fixdb_parser.add_argument ('--help', '-h', action='help', help='Справка')
 
 
    # Создаем trunk
    trunk_parser = subparsers.add_parser ('trunk', 
            add_help = False,
            help = 'Вызвать "контекст Астериск"',
            description = '''Регламентная нагрузка Астериск.''')
 
    # Создаем новую группу параметров
    trunk_group = trunk_parser.add_argument_group (title='Параметры')
 
    # Добавляем параметры
    trunk_group.add_argument ('trunk', type=str, action='store',
            help = 'Какой транк нагружать',
            metavar = 'Идентификатор')
 
    trunk_group.add_argument ("-v", "--verbose", action="store_true",
            help = 'Выводить диагностику')
 
    trunk_group.add_argument ('--help', '-h', action='help', help='Справка')

    # Создаем leadinka 
    leadinka_parser = subparsers.add_parser ('leadinka',
            add_help = False,
            help = 'HTTP запрос к Leadinka',
            description = '''Регламентное обращение к leadinka.com''')
     
    leadinka_parser.add_argument ('--help', '-h', action='help', help='Справка')
 
    # Создаем call
    call_parser = subparsers.add_parser ('call',
            add_help = False,
            help = 'Тестовый звонок на указанный номер',
            description = '''Тестовый звонок на указанный номер''')
 
    # Создаем новую группу параметров
    call_group = call_parser.add_argument_group (title='Параметры')
 
    # Добавляем параметры
    call_group.add_argument ('-t','--trunk', dest="trunk", type=str, default=None,
            help = 'Какой транк нагружать',
            metavar = 'Идентификатор')
 
    call_group.add_argument ('-p', '--phone', dest="phone", type=int, default=None,
            help = 'На какой номер звонить',
            metavar = '10 цифр номера (без 7ки)')
 
    call_group.add_argument ('-p2', '--phone2', dest="phone2", type=int, default=None,
            help = 'На какой номер звонить (второй)',
            metavar = '10 цифр номера (без 7ки)')

    call_group.add_argument ('--help', '-h', action='help', help='Справка')

    return parser

if __name__ == "__main__":
    parser = createParser()
    namespace = parser.parse_args(sys.argv[1:])

    switchFunc = {
        'migrate': Launcher.migrate,
        'fixdb':Launcher.fixdb,
        'trunk': Launcher.trunk,
        'call': Launcher.call,
        'leadinka': Launcher.leadinka
        }.get(namespace.command,None)
    if(switchFunc is None):
        parser.print_help()
    else:
        switchFunc(namespace)