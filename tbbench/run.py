# -*- coding: utf-8 -*-
"""

    tbbench.run
    -----------

    django-treebeard benchmarks

    :copyright: 2008 by Gustavo Picon
    :license: Apache License 2.0

"""

import collections, time, sys
from django.conf import settings
from django.db import transaction
from tbbench.models import TbNode, TbSortedNode, MpttNode, MpttSortedNode


## sample data

SEED = '791695346854615765126657163238313730700930615871063274726912112'
LOREM = ['lorem', 'ipsum', 'dolor', 'sit', 'amet', 'consectetur',
         'adipisicing', 'elit', 'sed', 'do', 'eiusmod', 'tempor',
         'incididunt', 'ut', 'labore', 'et', 'dolore', 'magna', 'aliqua',
         'ut', 'enim', 'ad', 'minim', 'veniam', 'quis', 'nostrud',
         'exercitation', 'ullamco', 'laboris', 'nisi', 'ut', 'aliquip',
         'ex', 'ea', 'commodo', 'consequat', 'duis', 'aute', 'irure',
         'dolor', 'in', 'reprehenderit', 'in', 'voluptate', 'velit',
         'esse', 'cillum', 'dolore', 'eu', 'fugiat', 'nulla', 'pariatur',
         'excepteur', 'sint', 'occaecat', 'cupidatat', 'non', 'proident',
         'sunt', 'in', 'culpa', 'qui', 'officia', 'deserunt', 'mollit',
         'anim', 'id', 'est', 'laborum']

## code

def nodedata_iter(seed, lorem, ids):
    while True:
        num = int(seed[0])
        if len(ids) < 10:
            id = None
        else:
            id = ids[0]
        yield num, lorem[0], id
        ids.rotate(num)
        lorem.rotate(num)
        seed.rotate(1)


def get_queues():
    seed = collections.deque(SEED)
    lorem = collections.deque(LOREM)
    ids = collections.deque([])
    return seed, lorem, ids


def insertion_test(nodemodel, numnodes):
    if not nodemodel:
        return
    seed, lorem, ids = get_queues()
    niter = nodedata_iter(seed, lorem, ids)
    while len(ids) < numnodes:
        numval, strval, parent_id = niter.next()
        if nodemodel in (TbNode, TbSortedNode):
            if parent_id:
                add_method = nodemodel.objects.get(id=parent_id).add_child
            else:
                add_method = nodemodel.add_root
            newobj = add_method(numval=numval, strval=strval)
        else:
            if parent_id:
                newobj = nodemodel.objects.create(numval=numval, strval=strval,
                    parent=nodemodel.objects.get(id=parent_id))
            else:
                newobj = nodemodel.objects.create(numval=numval, strval=strval)
            newobj.save()
        ids.append(newobj.id)
    return ids


def get_descendants(nodemodel, numnodes):
    if not nodemodel:
        return
    total = 0
    # retrieve all the descendants of all nodes, *lots* of times
    for i in range(10):
        for obj in nodemodel.objects.all():
            total += len(obj.get_descendants())
    return total


def moves_test(nodemodel, numnodes):
    if not nodemodel:
        return

    def move(nodemodel, node, target, pos):
        if nodemodel in (TbNode, TbSortedNode):
            node.move(target, pos)
        else:
            node.move_to(target, pos)

    if nodemodel in (TbNode, TbSortedNode):
        root_nodes_func = nodemodel.get_root_nodes
    else:
        root_nodes_func = nodemodel.tree.root_nodes
    possib = {TbNode: 'right',
              TbSortedNode: 'sorted-sibling',
              MpttNode: 'right',
              MpttSortedNode: 'right'}[nodemodel]
    poschild = {TbNode: 'last-child',
              TbSortedNode: 'sorted-child',
              MpttNode: 'last-child',
              MpttSortedNode: 'last-child'}[nodemodel]

    # move to root nodes (several times)
    for i in range(numnodes/10):
        move(nodemodel,
             root_nodes_func()[0],
             root_nodes_func().reverse()[0],
             possib)
    # move to child nodes
    while root_nodes_func().count() > 1:
        move(nodemodel,
             root_nodes_func().reverse()[0],
             root_nodes_func().all()[0],
             poschild)


def delete_test(nodemodel, numnodes):
    if not nodemodel:
        return
    while True:
        ids = [obj.id for obj in nodemodel.objects.all().reverse()[0:30]]
        if not len(ids):
            break
        nodemodel.objects.filter(id__in=ids).delete()
    nodemodel.objects.all().delete()



def measure(func, *args):
    time_start = time.time()
    func(*args)
    dur = time.time() - time_start
    return dur


def main():
    tests = [('Inserts', insertion_test),
             ('Descendants', get_descendants),
             ('Move', moves_test),
             ('Delete', delete_test)]
    tree_models = [
                   ('TB', TbNode),
                   ('TB Sorted', TbSortedNode),
                   ('MPTT', MpttNode),
                   ('MPTT Sorted', MpttSortedNode),
                   ]
    maxnodes = (100, 1000)
    maxnodes = (1000,)

    sys.stderr.write('\nBenchmarking... please wait.\n')
    results = {}
    for model_desc, model in tree_models:
        for numnodes in maxnodes:
            for want_tx in (False, True):
                for test_desc, test_func in tests:
                    key = (test_desc, numnodes, model_desc)
                    if not model:
                        res = None
                    else:
                        if want_tx:
                            func = transaction.commit_on_success(test_func)
                        else:
                            func = test_func
                        res = measure(func, model, numnodes)
                    sys.stderr.write('.')
                    sys.stderr.flush()
                    if key in results:
                        results[key].append(res)
                    else:
                        results[key] = [res]
    maxlen_test = max([len(test[0]) for test in tests])
    maxlen_model = max([len(model[0]) for model in tree_models])
    maxlen_num = len(str(max(maxnodes)))
    maxlen_dur = 7
    decimals_dur = 3
    output = []
    prev_test, prev_num = None, None
    for test_desc, test_func in tests:
        for numnodes in maxnodes:
            for model_desc, model in tree_models:
                ln1, ln2 = [], []
                if prev_test != test_desc:
                    ln1.append('+-%s-' % ('-' * maxlen_test,))
                    ln2.append('| %s ' % (test_desc.ljust(maxlen_test),))
                else:
                    tmpstr = '| %s ' % (' ' * maxlen_test,)
                    ln1.append(tmpstr)
                    ln2.append(tmpstr)
                if len(maxnodes) > 1:
                    if prev_num != numnodes:
                        ln1.append('+-%s-' % ('-' * maxlen_num,))
                        ln2.append('| %s ' % (str(numnodes).rjust(maxlen_num),))
                    else:
                        tmpstr = '| %s ' % (' ' * maxlen_num,)
                        ln1.append(tmpstr)
                        ln2.append(tmpstr)
                ln1.append('+-%s-' % ('-' * maxlen_model,))
                ln2.append('| %s ' % (model_desc.ljust(maxlen_model),))
                for dur in results[(test_desc, numnodes, model_desc)]:
                    ln1.append('+-%s-' % ('-' * maxlen_dur,))
                    if dur:
                        #ln2.append('| %s ' % ('%%%d.%df' % (maxlen_dur,
                        #           decimals_dur) % (dur,)))
                        ln2.append('| %s ' % ('%%%dd' % (maxlen_dur,) % (dur*1000,)))
                    else:
                        ln2.append('| %s ' % ('-'.ljust(maxlen_dur),))
                ln1.append('+')
                ln2.append('|')
                output.extend([''.join(ln1), ''.join(ln2)])
                prev_test, prev_num = test_desc, numnodes

    ln = ['+-%s-' % ('-' * maxlen_test,)]
    if len(maxnodes) > 1:
        ln.append('+-%s-' % ('-' * maxlen_num,))
    ln.extend(['+-%s-' % ('-' * maxlen_model,), 
               '+-%s-' % ('-' * maxlen_dur,),
               '+-%s-+' % ('-' * maxlen_dur,)])
    output.append(''.join(ln))

    sys.stdout.write('\n')
    print '\n'.join(output)



if __name__ == '__main__':
    main()
