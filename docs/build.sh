#!/bin/sh

DOC_OUTPUTDIR=../../docs
rm -f $DOC_OUTPUTDIR/*
rm -rf $DOC_OUTPUTDIR/_static/* $DOC_OUTPUTDIR/_sources/*
HTMLDIR=$DOC_OUTPUTDIR make -e html
