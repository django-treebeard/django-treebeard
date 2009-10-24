#!/bin/sh

DOC_OUTPUTDIR=.
cd $DOC_OUTPUTDIR
#rm -f $DOC_OUTPUTDIR/*
make clean
HTMLDIR=$DOC_OUTPUTDIR make -e html
rm -rf _build
