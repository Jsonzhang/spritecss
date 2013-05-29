"""CSS sprite finder"""

import re
import logging
from os import path

from . import SpriteRef
from .config import CSSConfig
from .css import split_declaration

logger = logging.getLogger(__name__)

bg_url_re = re.compile(r'\s*url\([\'"]?(.*?)[\'"]?\)\s*')
po_url_re = re.compile(r'(^-?\d+(%|in|cm|mm|em|ex|pt|pc|px)?)')

class NoSpriteFound(Exception): pass
class PositionedBackground(NoSpriteFound): pass

_pos_names = {"top":"0%",
              "center":"50%",
              "bottom":"100%",
              "right":"100%",
              "middle":"50%",
              "left":"0%"
            }
_pos_units = ("px", "%")

def _bg_positioned(val , sure_bg_position=False):
    parts = val.replace(';','')
    parts = parts.split()

    returnList = []
    if len(parts) >= 3 or sure_bg_position == True:
        for p in parts:
            if p in _pos_names:
                returnList.append(_pos_names[p])
            elif po_url_re.search(p):
                returnList.append(po_url_re.search(p).groups()[0])
    return returnList
def _bg_num_position(val , sure_bg_position = False):
    return _replace_sref_val(_bg_positioned(val , sure_bg_position))
def _replace_sref_val(position):
    returnList = []
    for i in position:
        if i.find('%')!=-1 or i.find('in')!=-1 or i.find('em')!=-1 or i.find('ex')!=-1 or i.find('pc')!=-1 or i.find('pt')!=-1 or i.find('mm')!=-1 or i.find('cm')!=-1:
            pass
        else:
            search_result = i.replace("px","")
            returnList.append(int(search_result))
            #search_result = i.replace("%","")
            #returnList.append(int(search_result)/100)
    return returnList

def _match_background_url(val):
    mo = bg_url_re.search(val)
    if not mo:
        return ""
    return mo.groups()[0]

def _match_background_position(val):
    pos = po_url_re.search(val)
    if not pos:
        raise NoSpriteFound(val)
    return pos

def get_background_url(val):
    return _match_background_url(val)
def get_background_position(val):
    return _match_background_position(val)
def get_Position(val , sure_bg_position = False):
        return _bg_positioned(val , sure_bg_position)

def find_decl_background_url(decl):
    (prop, val) = split_declaration(decl)
    if prop not in ("background", "background-image"):
        raise NoSpriteFound(decl)
    return get_background_url(val)

class SpriteEvent(object):
    lexeme = "spriteref"

    def __init__(self, ev, sprite):
        self.state = ev.state
        self.declaration = ev.declaration
        self.sprite = sprite

def iter_spriterefed(evs, conf=None, source=None, root=None):
    if source and not root:
        root = path.dirname(source)
    elif root and not source:
        source = path.join(root, "sprites.css")
    else:
        raise TypeError("specify at least source or root")
    if conf:
        normpath = conf.normpath
    else:
        normpath = CSSConfig(root=root).normpath

    for ev in evs:
        if ev.lexeme == "declaration":
            try:
                url = find_decl_background_url(ev.declaration)
            except NoSpriteFound:
                pass
            else:
                sprite = SpriteRef(normpath(url), source=source)
                ev = SpriteEvent(ev, sprite)
        yield ev

def find_sprite_refs(*args, **kwds):
    for ev in iter_spriterefed(*args, **kwds):
        if ev.lexeme == "spriteref":
            yield ev.sprite

def main():
    import sys
    import json
    from .css import CSSParser
    for fname in sys.argv[1:]:
        with open(fname, "rb") as fp:
            print >>sys.stderr, "extracting from", fname
            parser = CSSParser.read_file(fp)
            srefs = map(str, find_sprite_refs(parser, source=fname))
            v = [fname, srefs]
            json.dump(v, sys.stdout, indent=2)

if __name__ == "__main__":
    main()
