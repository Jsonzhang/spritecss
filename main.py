# -*- coding: utf-8 -*-
import sys
import logging
import optparse
from os import path, access, R_OK
from itertools import ifilter
from contextlib import contextmanager

from spritecss.css import CSSParser, print_css
from spritecss.config import CSSConfig
from spritecss.finder import find_sprite_refs
from spritecss.mapper import SpriteMapCollector, mapper_from_conf
from spritecss.packing import PackedBoxes, print_packed_size
from spritecss.packing.sprites import open_sprites
from spritecss.stitch import stitch
from spritecss.replacer import SpriteReplacer

logger = logging.getLogger(__name__) #spritecss.main

# TODO CSSFile should probably fit into the bigger picture
class CSSFile(object):
    def __init__(self, fname, conf=None):
        self.fname = fname
        self.conf = conf

    @contextmanager
    def open_parser(self):
        with open(self.fname, "rb") as fp:
            yield CSSParser.read_file(fp)

    @classmethod
    def open_file(cls, fname, conf=None):
        #cls is an instance of CSSFile
        #fname is the filename part
        with cls(fname).open_parser() as p:
            return cls(fname, conf=CSSConfig(p, base=conf, fname=fname))

    @property
    def mapper(self):
        return mapper_from_conf(self.conf)

    @property
    def output_fname(self):
        return self.conf.get_css_out(self.fname)

    def map_sprites(self):
        with self.open_parser() as p:
            #find_sprite_refs()将所有spriteref集合起来生成一个迭代器,迭代出来的是所有图片路径
            srefs = find_sprite_refs(p, conf=self.conf, source=self.fname)
            #test_sref 测试文件的访问权限
            def test_sref(sref):
                if not access(str(sref), R_OK):
                    logger.error("%s: not readable", sref); return False
                else:
                    logger.debug("%s passed", sref); return True
            #返回一个迭代器.如果参数二中的元素能让参数一的方法返回true则加入该返回的迭代器(这个迭代器是一个ifilter对象)
            return self.mapper.map_reduced(ifilter(test_sref, srefs))

class InMemoryCSSFile(CSSFile):
    def __init__(self, *a, **k):
        sup = super(InMemoryCSSFile, self)
        sup.__init__(*a, **k)
        with sup.open_parser() as p:
            self._evs = list(p)

    @contextmanager
    def open_parser(self):
        yield self._evs

def spritemap(css_fs, conf=None, out=sys.stderr):
    w_ln = lambda t: out.write(t + "\n")

    #: sum of all spritemaps used from any css files
    # smaps内存放所有CSS文件内的图片路径
    smaps = SpriteMapCollector(conf=conf)
    for css in css_fs:
        w_ln("mapping sprites in source %s" % (css.fname,))
        #这个步骤解析出图片路径 其中map.sprites解析出路径 collect负责将其改变成一个SpriteMap对象
        for sm in smaps.collect(css.map_sprites()):
            w_ln(" - %s" % (sm.fname,))

    # Weed out single-image spritemaps (these make no sense.)
    # 如果整个CSS文件内只有一个图片路径就不要白费力气了亲.如果有多个那么就由smaps先森来管理你们吧
    smaps = [sm for sm in smaps if len(sm) > 1]

    sm_plcs = []
    #smaps 内包含所有CSS文件的所有图片路径,smap包含的则是一个CSS文件的所有图片路径
    for smap in smaps:
        #sprites中包含SpriteNode对象,其中有每一个精灵及其具体的属性
        with open_sprites(smap, pad=conf.padding) as sprites:
            w_ln("packing sprites in mapping %s" % (smap.fname,))
            logger.debug("annealing %s in steps of %d",
                         smap.fname, conf.anneal_steps)
            packed = PackedBoxes(sprites, anneal_steps=conf.anneal_steps)
            print_packed_size(packed)
            #packed.placements存储的是新图像的sprite位置信息
            #smap存储的是新图像中的sprite元信息
            sm_plcs.append((smap, packed.placements))

            w_ln("writing spritemap image at %s" % (smap.fname,))
            #im包含的是sprites的元素,用于写入到新的大sprites中
            im = stitch(packed)
            with open(smap.fname, "wb") as fp:
                im.save(fp)

    replacer = SpriteReplacer(sm_plcs)
    for css in css_fs:
        w_ln("writing new css at %s" % (css.output_fname,))
        with open(css.output_fname, "wb") as fp:
            print_css(replacer(css), out=fp)

op = optparse.OptionParser()
op.set_usage("%prog [opts] <css file(s) ...>")
op.add_option("-c", "--conf", metavar="INI",
              help="read base configuration from INI")
op.add_option("--padding", type=int, metavar="N",
              help="keep N pixels of padding between sprites")
op.add_option("-v", "--verbose", action="store_true",
              help="use debug logging level")
#op.add_option("--in-memory", action="store_true",
#              help="keep CSS parsing results in memory")
#op.add_option("--anneal", type=int, metavar="N", default=9200,
#              help="simulated anneal steps (default: 9200)")
op.set_default("in_memory", False)
op.set_default("anneal", None)

def main():
    (opts, args) = op.parse_args()

    logging.basicConfig(level=logging.DEBUG if opts.verbose else logging.INFO)

    if not args:
        op.error("you must provide at least one css file")

    if opts.in_memory:
        css_cls = InMemoryCSSFile
    else:
        css_cls = CSSFile

    base = {}

    if opts.conf:
        from ConfigParser import ConfigParser
        cp = ConfigParser()
        with open(opts.conf) as fp:
            cp.readfp(fp)
        base.update(cp.items("spritemapper"))
    if opts.anneal:
        base["anneal_steps"] = opts.anneal
    if opts.padding:
        base["padding"] = (opts.padding, opts.padding)

    conf = CSSConfig(base=base)

    spritemap([css_cls.open_file(fn, conf=conf) for fn in args], conf=conf)

if __name__ == "__main__":
    main()
