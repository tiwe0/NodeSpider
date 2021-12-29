from scrapy import Selector
from requests import Session
from collections.abc import Iterator
from itertools import chain
import time
import sys


class BaseNode:
    def __init__(self, _name, _input=None):
        self._name = _name
        self._input = _input
        self._middle = None
        self._output = None
        self._child = []
        self._parent = None
        self._controller = None
        self._statu = "OUTED"

    def __getitem__(self, key):
        return self._child[key]

    def __repr__(self):
        detail = f"""
        Node [{self._statu[0]}]: {self._name}
        _input: {self._input}
        middle: {self._middle}
        output: {self._output}
        """
        return detail

    def _clear_input(self):
        self._input = None

    def _clear_output(self):
        self._output = None

    def _add_child(self, node):
        self._child.append(node)
        node._parent = self

    def _is_leaf(self):
        return not self._child

    def _contain_something(self):
        contain_something = self._middle._contain_something()
        if contain_something:
            self._statu = "ACTIVATED"
        else:
            self._statu = "OUTED"
        return contain_something

    def _fetch_one_piece(self):
        if not self._contain_something():
            return None
            raise StopIteration
        return self._middle._fetch_one_piece()

    def _input_to_middle(self):
        _input = self._input
        _middle = self.api_input_to_middle(_input)
        self._middle = MyIterator(_middle)
        self._clear_input()

    # HACK 测试使用
    def api_input_to_middle(self, _input):
        try:
            pre_data = _input
        except Exception:
            print(f"ERROR IN {self._name}")
            sys.exit(0)
        return (pre_data + f"_by_[{self._name}_{i}]" for i in range(5))

    def _output_to_child_leaf(self):
        print(self._output)
        self._clear_output()

    def _middle_to_output(self):
        one_piece = self._fetch_one_piece()
        self._output = one_piece

    def _output_to_child(self):
        if self._is_leaf():
            self._output_to_child_leaf()
            return
        for child in self._child:
            child._input = self._output
        self._clear_output()

    # CORE
    def activate(self):
        print(f"ACTIVE: {self._name}")
        # time.sleep(1)
        if self._statu == "OUTED":
            self._input_to_middle()
        self._middle_to_output()
        if self._statu == "ACTIVATED":
            self._output_to_child()


class MyIterator:
    def __init__(self, iterator):
        if not isinstance(iterator, Iterator):
            iterator = iter(iterator)
        self._container = iterator

    def _fetch_one_piece(self):
        try:
            one_piece = next(self._container)
        except StopIteration:
            one_piece = None
        return one_piece

    def _contain_something(self):
        one_piece = self._fetch_one_piece()
        if one_piece:
            self._container = chain([one_piece], self._container)
            return True
        return False


class Controller:
    def __init__(self, header):
        self._header = header
        self._pool = LeafPool(header)
        self._nodes = self._get_all_nodes()
        self._register_nodes()
        self._collect = []
        self._statu = "ACTIVATED"

    def _register_nodes(self):
        for node in self._nodes:
            node._controller = self

    def _get_all_nodes(self):
        result = []

        def walk(node):
            if not node:
                return
            result.append(node)
            for child in node._child:
                walk(child)

        walk(self._header)
        return result

    def _clear_collect(self):
        self._collect = []

    def activate_init(self):
        if self._collect:
            for node in self._collect:
                self.activate_rec_without_leaf(node)
            self._collect = []
            return
        self.activate_rec_without_leaf(self._header[0])

    @staticmethod
    def activate_rec_without_leaf(node):
        if node._is_leaf():
            return
        node.activate()
        if node._statu == "ACTIVATED":
            for child in node._child:
                Controller.activate_rec_without_leaf(child)
        return

    @staticmethod
    def activate_rec(node):
        if not node:
            return
        node.activate()
        if node._statu == "ACTIVATED":
            for child in node._child:
                Controller.activate_rec(child)
        return

    def start_loop(self):
        self._pool.loop()

    def start_engine(self):
        while True:
            print("ACTIVATE_INIT")
            self.activate_init()

            print("START LOOP")
            self.start_loop()

            print("LOOKUP")
            for leaf in self._pool:
                self.lookup_to_outed(leaf)

            if self._statu == "FINISHED":
                break

    def lookup_to_outed(self, node):
        if node._name == "header":
            self._statu = "FINISHED"
            return
        if not node:
            return
        if node in self._collect:
            return
        if node._is_leaf():
            self.lookup_to_outed(node._parent)
            return
        _contain_something = node._contain_something()
        if not _contain_something:
            self.lookup_to_outed(node._parent)
            return
        else:
            self._collect.append(node)


class LeafPool:
    def __init__(self, header):
        self._pool = []
        self._seek_leaves(header)

    def __repr__(self):
        return f"Leaf-Pool Contain {self._pool}"

    def __getitem__(self, key):
        return self._pool[key]

    def _add_leaf(self, leaf):
        self._pool.append(leaf)

    def _seek_leaves(self, header):
        if not header:
            return
        if header._is_leaf():
            self._add_leaf(header)
            return
        for child in header._child:
            self._seek_leaves(child)

    def loop(self):
        n = len(self._pool)
        pool = self._pool
        _ = 0
        while True:
            leaf = pool[_]
            leaf.activate()
            if leaf._statu == "OUTED" and _ == (n-1):
                break
            _ += 1
            if _ == n:
                _ = 0
        print("pool loop break")
        return


class FileNode(BaseNode):
    def __init__(self, _name, _file_path):
        super().__init__(_name, _file_path)

    def api_input_to_middle(self, _file_path):
        with open(_file_path, "rt") as f:
            for _ in f:
                yield _


class FetchNode(BaseNode):
    _header = {
        "User-Agent": "Google Bot"
    }

    def __init__(self, _name, _select="a::attr(href)"):
        super().__init__(_name)
        self._session = Session()
        self._session.headers = self._header
        self._select = _select

    def api_input_to_middle(self, _url):
        resp = self._session.get(_url)
        selector = Selector(text=resp.text)
        s = selector.css(self._select)
        for _ in s:
            yield _


def test_1():
    header = BaseNode("header")
    node_1 = BaseNode("file")
    node_2 = BaseNode("url")
    node_3 = BaseNode("item_left")
    node_4 = BaseNode("item_right")

    header._add_child(node_1)
    node_1._add_child(node_2)
    node_2._add_child(node_3)
    node_2._add_child(node_4)

    def walk(node):
        print(node)
        for child in node._child:
            walk(child)

    def debug_see_tree():
        walk(node_1)

    print("SET _input")
    node_1._input = "ITEM"

    print("BUILD Controller")
    controller = Controller(header)
    controller.start_engine()

    print("test_1 passed")


if __name__ == "__main__":
    test_1()
