#!/usr/bin/env bash

mix_txt="mix.txt"
mix_zip="mix.zip"
v2rayn_txt="vnn.txt"
v2rayn_zip="vnn.zip"
separate_zip="sep.zip"

echo "copy all files"
cat -- "tmp/links/"*.txt | sort | uniq | shuf > "tmp/${mix_txt}"

echo "filter v2rayn://..."
cat -- "tmp/${mix_txt}" |  grep "^v2rayn://" > "tmp/${v2rayn_txt}"

echo "create zip files:"
zip "tmp/${separate_zip}" tmp/links/*.txt
zip "tmp/${mix_zip}" "tmp/${mix_txt}"
zip "tmp/${v2rayn_zip}" "tmp/${v2rayn_txt}"

echo "total lines:"
c_mix=$(wc -l "tmp/${mix_txt}" | awk '{print $1}')
echo "MIX_COUNT=${c_mix}" | tee -a "${GITHUB_STEP_SUMMARY}" "${GITHUB_ENV}"

c_v2rayn=$(wc -l "tmp/${v2rayn_txt}" | awk '{print $1}')
echo "V2RAYN_COUNT=${c_v2rayn}" | tee -a "${GITHUB_STEP_SUMMARY}" "${GITHUB_ENV}"
