#!/bin/bash

files=(`ls *.py`)

mkdir -p docs
for file in ${files[@]}; do
	pdoc3 --html --force --output-dir ./docs ./${file}
done
