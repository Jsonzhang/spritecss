# coding=utf-8
"Replaces references to sprites with offsetted background declarations."

import logging

from . import SpriteRef
from .css import split_declaration
from .finder import NoSpriteFound, get_background_url , get_Position, _replace_sref_val

logger = logging.getLogger(__name__)

def _build_pos_map(smap, placements):
    """Build a dict of sprite ref => pos."""
    return dict((n.fname, p) for (p, n) in placements)


class SpriteReplacer(object):
    def __init__(self, spritemaps):
        self._smaps = dict((sm.fname, _build_pos_map(sm, plcs))
                           for (sm, plcs) in spritemaps)

    def __call__(self, css):
        with css.open_parser() as p:
            for ev in p:
                if ev.lexeme == "declaration":
                    ev = self._replace_ev(css, ev)
                elif ev.lexeme == "block_end":
                    ev.background_position = []
                yield ev

    def _replace_ev(self, css, ev):
        (prop, val) = split_declaration(ev.declaration)
        if prop == "background":
            try:
                url = get_background_url(val)
                position = get_Position(val)
            except NoSpriteFound:
                pass
            else:
                sref = SpriteRef(css.conf.normpath(url), source=css.fname , position = position)#问题所在!!!!
                try:
                    new = self._replace_val(css, ev, sref)
                except KeyError:
                    new = val
                ev.declaration = "%s: %s" % (prop, new)
        elif prop == "background-position":
            ev.background_position = []
        elif prop == "width" or prop == "height":
            pass
        return ev

    def _replace_val(self, css, ev, sref):
        sm_fn = css.mapper(sref) #配置参数
        #计算出来的位置 sm_fn是不同CSS文件集合成不同Sprite
        #这里生成的dict是用SpriteRef来作为key值的
        pos = self._smaps[sm_fn][sref]

        if(sref.position):
            oldpos = _replace_sref_val(sref.position)
            newpos = (pos[0]+oldpos[0],pos[1]+oldpos[1])

        sm_url = css.conf.get_spritemap_url(sm_fn)
        sm_url = sm_url.replace('\\','/')
        logger.debug("replace bg %s at L%d with spritemap %s at %s",
                     sref, ev.state.token.line_no, sm_url, pos)

        parts = ["url('%s')" % (sm_url,), "no-repeat"]
        for r in newpos:
            parts.append(("-%dpx" % r) if r else "0")
        return " ".join(parts)
