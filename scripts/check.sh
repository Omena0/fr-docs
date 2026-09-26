
: Runs lint and checkers

echo Ruff checks + format
ruff check . --fix --unsafe-fixes
ruff format .

echo
echo Refurb checks
refurb --enable-all .

