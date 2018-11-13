#!/bin/bash
# script to automatically generate the psyplot api documentation using
# sphinx-apidoc and sed
sphinx-apidoc -f -M -e  -T -o api ../psy_strat/
# replace chapter title in psy_strat.rst
sed -i -e 1,1s/.*/'API Reference'/ api/psy_strat.rst

sphinx-autogen -o generated *.rst
