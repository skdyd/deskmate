# Runs outside the MSIX container (via install_touch.lnk): copies settings\touch-prompts.json to the real
# %APPDATA%\deskmate (only if missing, so user edits are kept) and marks big-head models as "chibi" for touch areas.
import json, os, shutil
root = r'C:\Users\jywhy\Desktop\deskmate AI'
ud = os.path.join(os.environ['APPDATA'], 'deskmate')
log = []
dst = os.path.join(ud, 'touch-prompts.json')
if not os.path.exists(dst):
    shutil.copy2(os.path.join(root, 'settings', 'touch-prompts.json'), dst); log.append('copied touch-prompts.json')
else:
    log.append('touch-prompts.json exists, kept')
for cid in ('teto', 'furina'):
    p = os.path.join(ud, 'character', cid, 'character.json')
    j = json.load(open(p, encoding='utf-8'))
    if j.get('touchLayout') != 'chibi':
        j['touchLayout'] = 'chibi'
        json.dump(j, open(p, 'w', encoding='utf-8'), ensure_ascii=False, indent=2); log.append(f'{cid} chibi')
open(os.path.join(root, 'logs', 'install_touch.log'), 'w', encoding='utf-8').write('\n'.join(log) + '\ndone\n')
