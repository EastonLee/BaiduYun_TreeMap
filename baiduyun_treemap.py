#coding=utf-8
__author__ = 'easton'
from pprint import pprint, pformat
from ast import literal_eval
import re, json, unittest, os
from baidupcsapi import PCS

THIS = 'this'
SUB = 'sub'

def ea_print(to_print, layer=0):
    """
    pprint can't handle uncode/str in list/dict
    """
    if isinstance(to_print, list):
        print '\t'*layer, '['
        for i in to_print:
            ea_print(i, layer+1)
            print '\t'*layer, ','
        print '\t'*layer, ']'
        return
    elif isinstance(to_print, dict):
        print '\t'*layer, '{'
        for key, value in to_print.iteritems():
            print '\t'*layer, key, '\t:'
            ea_print(value, layer+1)
        print '\t'*layer, '}'
        return
    elif isinstance(to_print, (str, unicode, int, float)):
        if isinstance(to_print, float):
            print '\t'*layer, to_print, 'MB,'
        else:
            print '\t'*layer, to_print, ','
    else:
        raise Exception('unexpected type', type(to_print), to_print)

def literalize_str_or_list_or_dict(para):
    """
    baiduyun returned json is escaped, and started with \\\\
    :rtype: unicode, list, dict
    >>> print literalize_str_or_list_or_dict(r"\u5496".decode('unicode_escape'))
    咖
    """
    try:
        some_object_iterator = iter(para)
    except TypeError as te:
        pass
    else:
        if isinstance(para, list):
            return [literalize_str_or_list_or_dict(i) for i in para]
        if isinstance(para, dict):
            return {key: literalize_str_or_list_or_dict(value) for key, value in para.iteritems()}
    if not isinstance(para, str):
        return para

    # str remains till now
    literal = para.decode('unicode_escape')
    return re.sub(r'\\', '', literal)

def gen_root_dir_tree_as_json(username, password, output_filepath):
    pcs = PCS(username, password)
    d3_treemap = gen_dir_tree(pcs, '/', True)
    dir_tree_str = json.dumps(d3_treemap, ensure_ascii=False, sort_keys=True, indent=4, separators=(',', ': '))
    dir_tree_str = dir_tree_str.encode('utf-8')
    print dir_tree_str
    with open(output_filepath, 'w') as outfile:
        outfile.write(dir_tree_str)
    print 'baiduyun storage dir tree stored as ' + output_filepath

def gen_dir_tree(pcs, from_where_str, use_d3js_struct=False):
    """
    :type from_where_str: str
    :type use_d3js_struct: bool
    :return:
    """
    assert isinstance(from_where_str, (str, unicode)), from_where_str
    try:
        my_struct_tree = {}
        d3js_struct_tree = {}
        my_struct_tree[THIS] = {'name': from_where_str, 'files': 0, 'size': 0}
        d3js_struct_tree['name'] = from_where_str
        from_where = pcs.list_files(from_where_str).content
        from_where = literal_eval(from_where)
        if from_where['errno']:
            raise Exception(from_where_str, from_where)
        from_where = literalize_str_or_list_or_dict(from_where)
        my_struct_tree[SUB] = []
        d3js_struct_tree['children'] = []
        if len(from_where['list']) == 0:
            return d3js_struct_tree if use_d3js_struct else my_struct_tree
        for i in from_where['list']:
            sub_path = i['path']
            if i['isdir']:
                if use_d3js_struct:
                    d3js_struct_tree['children'].append(gen_dir_tree(pcs, sub_path, use_d3js_struct))
                else:
                    my_struct_tree[SUB].append(gen_dir_tree(pcs, sub_path, use_d3js_struct))
            else:
                if use_d3js_struct:
                    d3js_struct_tree['children'].append({
                        'name': i['server_filename'],
                        'size': i['size']/1024./1024.
                    })
                else:
                    my_struct_tree[SUB].append({'name': i['server_filename'],
                                     'size': i['size']/1024./1024.,
                                     'files': 1})

        for i in my_struct_tree[SUB]:
            if THIS in i:
                my_struct_tree[THIS]['size'] += i[THIS]['size']
                my_struct_tree[THIS]['files'] += i[THIS]['files']
            else:
                my_struct_tree[THIS]['size'] += i['size']
                my_struct_tree[THIS]['files'] += 1
        return d3js_struct_tree if use_d3js_struct else my_struct_tree
    except :# TODO: KeyboardInterrupt:
        my_struct_tree = {'name': from_where_str, 'unfinished': True}
        if from_where_str.__eq__('/'):
            pass # TODO: save progress
        else:
            return my_struct_tree
        raise

def serve_treemap_page():
    import SimpleHTTPServer
    import SocketServer

    PORT = 8002
    Handler = SimpleHTTPServer.SimpleHTTPRequestHandler
    httpd = SocketServer.TCPServer(("", PORT), Handler)
    print "serving at port", PORT
    httpd.serve_forever()

class Test(unittest.TestCase):
    """
    """
    def setUp(self):
        self.username = 'YOUR_BAIDU_ACCOUNT_USERNAME'
        self.password = 'YOUR_BAIDU_ACCOUNT_PASSWORD'
        self.root = '/'

    def test_download(self):
        pcs = PCS(self.username, self.password)
        print 'Quota :'
        pprint(literal_eval( pcs.quota().content))
        headers = {'Range': 'bytes=0-99'}
        r = pcs.download('/test.txt', headers=headers)
        print '/test.txt content:'
        print r.content

    def test_list(self):
        pcs = PCS(self.username, self.password)
        print 'content of BaiduYun root dir'
        ea_print((literalize_str_or_list_or_dict(literal_eval(pcs.list_files(self.root).content))))

if __name__ == '__main__':
    #unittest.main()
    #import doctest
    #doctest.testmod()

    import os
    if not os.path.exists(os.path.join(os.path.dirname(__file__), 'treemap_data.json')):
        gen_root_dir_tree_as_json('YOUR_BAIDU_ACCOUNT_USERNAME', 'YOUR_BAIDU_ACCOUNT_PASSWORD', 'treemap_data.json')
    import webbrowser
    webbrowser.open('http://localhost:8002/treemap_header_05.html')
    serve_treemap_page()
