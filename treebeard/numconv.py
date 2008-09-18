# -*- coding: utf-8 -*-

# ----------------------------------------------------------------------------
# numconv
# Copyright (c) 2008 Gustavo Picon
# All rights reserved.
# 
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions 
# are met:
#
#  * Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
#  * Redistributions in binary form must reproduce the above copyright 
#    notice, this list of conditions and the following disclaimer in
#    the documentation and/or other materials provided with the
#    distribution.
#  * Neither the name of numconv nor the names of its
#    contributors may be used to endorse or promote products
#    derived from this software without specific prior written
#    permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS
# FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE
# COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT,
# INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING,
# BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN
# ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
# ----------------------------------------------------------------------------

"""

numconv 1.0 - http://code.google.com/p/numconv/

Python library to convert strings to numbers and numbers to strings.
Can take custom alphabets for encoding/decoding.

For examples on how to use this library, open the included tests.py file
or go to:
http://code.google.com/p/numconv/source/browse/trunk/tests.py


"""

VERSION = (1, 0)

# from april fool's rfc 1924
BASE85 = '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz' \
         '!#$%&()*+-;<=>?@^_`{|}~'

# rfc4648 alphabets
BASE16 = BASE85[:16]
BASE32 = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ234567'
BASE32HEX = BASE85[:32]
BASE64 = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/'
BASE64URL = BASE64[:62] + '-_'

# cached maps
CMAPS = {}


def int2str(num, radix=10, alphabet=BASE85):
    """Converts an integer into a string."""
    if alphabet not in CMAPS:
        # just to validate the alphabet
        getcmap(alphabet)
    if int(num) != num:
        raise TypeError, 'number must be an integer'
    if num < 0:
        raise ValueError, 'number must be positive'
    if int(radix) != radix:
        raise TypeError, 'radix must be an integer'
    if not 2 <= radix <= len(alphabet):
        raise ValueError, 'radix must be >= 2 and <= %d' % (len(alphabet),)
    ret = ''
    while True:
        ret = alphabet[num % radix] + ret
        if num < radix:
            break
        num //= radix
    return ret

def str2int(num, radix=10, alphabet=BASE85):
    """Converts a string into an integer."""
    if alphabet not in CMAPS:
        getcmap(alphabet)
    if int(radix) != radix:
        raise TypeError, 'radix must be an integer'
    if not 2 <= radix <= len(alphabet):
        raise ValueError, 'radix must be >= 2 and <= %d' % (len(alphabet),)
    if radix <= 36 and alphabet[:radix].lower() == BASE85[:radix].lower():
        return int(num, radix)
    ret = 0
    lmap = CMAPS[alphabet]
    lalphabet = alphabet[:radix]
    for char in num:
        if char not in lalphabet:
            raise ValueError, "invalid literal for radix2int() " \
                "with radix %d: '%s'" % (radix, num)
        ret = ret * radix + lmap[char]
    return ret

def getcmap(alphabet):
    """Builds an internal alphabet lookup table, to be stored in CMAPS"""
    ret = dict(zip(alphabet, range(len(alphabet))))
    if len(ret) != len(alphabet):
        raise ValueError, "duplicate characters found in '%s'" % (alphabet,)
    CMAPS[alphabet] = ret
    return ret

