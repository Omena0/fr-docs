
: Runs lint and checkers

echo Ruff checks
ruff check . --fix --unsafe-fixes

echo
echo Refurb checks
refurb --enable-all .

