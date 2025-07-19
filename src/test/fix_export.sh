#!/bin/bash
conda env list | awk '!/^#/ && !/conda/ {gsub(/\*/, "", $1); if ($1 != "" && $1 != $NF && $1 !~ /\//) print $1}' | while read env; do
    conda env export -n "$env" > "/tmp/${env}.yml"
done
