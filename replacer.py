# coding=utf-8
"Replaces references to sprites with offsetted background declarations."

import logging

from . import SpriteRef
from .css import split_declaration
from .finder import NoSpriteFound, get_background_url , _replace_sref_val, _bg_num_position, _bg_positioned

logger = logging.getLogger(__name__)
target_prop = ("background","background-image")
def _build_pos_map(smap, placements):
    """Build a dict of sprite ref => pos."""
    return dict((n.fname, p) for (p, n) in placements)


class SpriteReplacer(object):
    def __init__(self, spritemaps):
        self._smaps = dict((sm.fname, _build_pos_map(sm, plcs))
                           for (sm, plcs) in spritemaps)

    def __call__(self, css):
        group_background = ""
        onlybackground = ""
        with css.open_parser() as p:
            for ev in p:
                if ev.lexeme == "declaration":
                    ev = self._replace_ev(css, ev , group_background)
                    (declaration_name,declaration_value) =  split_declaration(ev.declaration)
                    if declaration_name in target_prop:
                        ev.declaration =  ev.declaration
                        group_background = ev.declaration
                        onlybackground = ev
                    else:
                        yield ev
                elif ev.lexeme == "block_end":
                    group_background = ""
                    if onlybackground:
                        yield onlybackground
                        yield ev
                    else:
                        yield ev
                else:
                    yield ev

    def _replace_ev(self, css, ev ,group_background):
        (prop, val) = split_declaration(ev.declaration)
        if prop.strip() in target_prop:
            try:
                url = get_background_url(val)
            except NoSpriteFound:
                 pass
            else:
                sref = SpriteRef(css.conf.normpath(url), source=css.fname , position = [])
                try:
                    new = self._replace_val(css, ev, sref)
                except KeyError:
                    new = val
                ev.declaration = "background: %s" % (new)
        elif prop == "background-position" and group_background:
            newPos = _bg_num_position(val,True)
            oldpos = _bg_num_position(group_background)
            newVal = group_background.replace(str(oldpos[0]),str(oldpos[0]+newPos[0]))
            newVal = newVal.replace(str(oldpos[1]),str(oldpos[1]+newPos[1]))
            ev.declaration = newVal
        return ev

    def _replace_val(self, css, ev, sref):
        sm_fn = css.mapper(sref) #配置参数
        #计算出来的位置 sm_fn是不同CSS文件集合成不同Sprite
        #这里生成的dict是用SpriteRef来作为key值的
        pos = self._smaps[sm_fn][sref]

        #if(sref.position):
        oldpos = _replace_sref_val(sref.position)
        newpos = (-(pos[0]-oldpos[0]),-(pos[1]-oldpos[1]))

        sm_url = css.conf.get_spritemap_url(sm_fn)
        sm_url = sm_url.replace('\\','/')
        logger.debug("replace bg %s at L%d with spritemap %s at %s",
                     sref, ev.state.token.line_no, sm_url, pos)

        parts = ["url('%s')" % (sm_url,), "no-repeat"]
        for r in newpos:
            parts.append(("%dpx" % r) if r else "0px")
        return " ".join(parts)
