#!/bin/sh

BASEDIR=../../docs
rm -rf $BASEDIR/_static/* $BASEDIR/_sources/*
rm -r $BASEDIR/*
HTMLDIR=$BASEDIR make -e html
