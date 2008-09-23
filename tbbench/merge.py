import glob
import sys


data = {}
basedb = None
for fname in glob.glob('./tbbench-*'):
    dbname = fname.split('-')[1]
    data[dbname] = []
    for ln in open(fname):
        if ln[0] not in ('+|'):
            continue
        data[dbname].append(ln.rstrip())
    if len(data[dbname]):
        basedb = dbname

if not basedb:
    sys.stderr.write("Couldn't find valid files\n")
    sys.exit(-1)

dbnames = data.keys()
dbnames.sort()
lengths = [len(val) for val in data.values()]
basepos = len(data[basedb][0].rstrip('+').rstrip('-').rstrip('+').rstrip('-'))

ltop, l1, lmid, l2, lbot = [], [], [], [], []
ltop.append('+%s+' % ('-' * (basepos-2),))
lbot.append(data[basedb][0][0:basepos])
for ln in (l1, l2):
    ln.append('|%s|' % (' ' * (basepos-2),))
lmid.append('|%s+' % (' ' * (basepos-2),))
for dbname in dbnames:
    if not len(data[dbname]):
        continue
    aux = data[dbname][0][basepos:]
    ltop.append('%s+' % ('-' * (len(aux)-1),))
    for ln in (lmid, lbot):
        ln.append(aux)
    rlen = len(aux)
    l1.append(' %s |' % (dbname.center(rlen-3),))
    for tx in ('no tx', 'tx'):
        l2.append(' %s |' % (tx.center(rlen/2-3),))
for ln in (ltop, l1, lmid, l2):
    print ''.join(ln)
print ''.join(lbot).replace('-', '=')
for num in range(1, len(data[basedb])):
    ln = []
    ln.append(data[basedb][num][0:basepos])
    for dbname in dbnames:
        if not len(data[dbname]):
            continue
        ln.append(data[dbname][num][basepos:])
    print ''.join(ln)

