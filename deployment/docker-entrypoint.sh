
ROOT=/work/

cd $ROOT || exit 1
#cd /work/OpusCleaner/frontend && npm run dev & 
opuscleaner-server serve --reload
