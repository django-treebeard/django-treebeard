#!/bin/sh

DOC_OUTPUTDIR=../../docs
rm -rf $DOC_OUTPUTDIR/_static/* $DOC_OUTPUTDIR/_sources/*
rm -r $DOC_OUTPUTDIR/*
HTMLDIR=$DOC_OUTPUTDIR make -e html
