#!/usr/bin/env python
# -*- coding: UTF-8 -*-
#
# Lookup word from YoDao online dictionary service.
#

import sys, urllib2, optparse, os
try:
    import xml.etree.ElementTree as ElementTree # in python >=2.5
except ImportError:
    try:
        import cElementTree as ElementTree # effbot's C module
    except ImportError:
        try:
            # effbot's pure Python module
            import elementtree.ElementTree as ElementTree
        except ImportError:
            try:
                # ElementTree API using libxml2
                import lxml.etree as ElementTree
            except ImportError:
                import warnings
                warnings.warn("could not import ElementTree "
                              "(http://effbot.org/zone/element-index.htm)")

def parseDict(xml):
    tree = ElementTree.fromstring(xml)
    word = tree.find('original-query').text
    customtrans = tree.findall('custom-translation')
    translist = []
    for node in customtrans:
        temp =[]
        for item in deepFindAll(node,'translation/content'):
            temp.append(item.text)
        translist.append([node.find('source/name').text,temp])
    return word, translist

def parseSentence(xml):
    tree = ElementTree.fromstring(xml)
    senlist = []
    for node in deepFindAll(tree,'example-sentences/sentence-pair'):
        senlist.append([node.find('sentence').text,
            node.find('sentence-translation').text])
    return senlist

def deepFindAll(element, tag):
    if type(tag) == type(''):       tag = tag.split('/')
    if tag == []:        return  [element]
    if len(tag) == 1:
        elist = []
        findres = element.findall(tag[0])
        if findres:     elist.extend(findres)
        for node in element:
            elist.extend(deepFindAll(node, tag[0]))
        return elist
    else:
        sublist = deepFindAll(element, tag[0])
        return deepFindAll(element, tag[1:])

if __name__=='__main__':
    parser = optparse.OptionParser()
    parser.add_option('-w', dest='word',action='store_true',
            default=False, help='print the translation of the word.')
    parser.add_option('-s', dest='sent',action='store_true',
            default=False, help='print sample sentences.')
    options, args = parser.parse_args(sys.argv[1:])
    #test if the string contains chinese
    #if ' '.join(args).isalpha():
    #    #os.system('echo %s |festival --tts' %' '.join(args))
    #    os.system('espeak -ven+13 %s &>/dev/null' %' '.join(args))
    #get word translation
    xml1= urllib2.urlopen("http://dict.yodao.com/search?keyfrom=dict.python&q=" + '+'.join(args) + "&xmlDetail=true&doctype=xml").read()
    word, translist = parseDict(xml1)
    #get sample sentences
    xml2= urllib2.urlopen("http://dict.yodao.com/search?keyfrom=dict.python&q=lj:" + '+'.join(args) + "&xmlDetail=true&doctype=xml").read()
    senlist = parseSentence(xml2)
    #define colors
    BOLD='\033[1m'
    DEFAULT='\033[m'
    UNDERLINE='\033[4m'
    MAGENTA='\033[35m'
    YELLOW='\033[33m'
    GREEN='\033[32m'
    RED='\033[31m'
    WHITE='\033[37m'
    BGWHITE='\033[47m'
    BLUE='\033[34m'
    if options.word:
        print RED+BOLD+word+DEFAULT
        for item in translist:
            print MAGENTA+BGWHITE+item[0]+DEFAULT +': '\
                +GREEN+BOLD+ '; '.join(item[1]) + DEFAULT
    if options.sent:
        for item in senlist:
            print item[0].replace('<b>', YELLOW+BOLD).replace('</b>', DEFAULT)
            print BLUE+BOLD+item[1]+DEFAULT
    if not options.word and not options.sent:
        print RED+BOLD+word+DEFAULT
        for item in translist:
            print MAGENTA+BGWHITE+item[0]+DEFAULT +': '\
                +GREEN+BOLD+ '; '.join(item[1]) + DEFAULT
        for item in senlist[:7]:
            print item[0].replace('<b>', YELLOW+BOLD).replace('</b>', DEFAULT)
            print BLUE+BOLD+item[1]+DEFAULT
