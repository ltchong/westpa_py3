#!/bin/bash

if [ -n "$SEG_DEBUG" ] ; then
    set -x
    env | sort
fi

# Make a temporary file in which to store output from cpptraj
TEMP=$(mktemp)

cd $WEST_SIM_ROOT

# Load the restart (.rst) file into cpptraj and calculate the distance between
# the Na+ and Cl- ions. Here, $WEST_STUCT_DATA_REF indicates a particular 
# $WEST_ISTATE_DATA_REF, as defined by gen_istate.sh
COMMAND="           parm $WEST_SIM_ROOT/amber_config/nacl.parm7 \n"
COMMAND="${COMMAND} trajin $WEST_STRUCT_DATA_REF \n"
COMMAND="${COMMAND} distance na-cl :1@Na+ :2@Cl- out $TEMP \n"
COMMAND="${COMMAND} go"
echo -e "${COMMAND}" | $CPPTRAJ

# Pipe the relevant part of the output file (the distance) to $WEST_PCOORD_RETURN
cat $TEMP | tail -n +2 | awk '{print $2}' > $WEST_PCOORD_RETURN
rm $TEMP

if [ -n "$SEG_DEBUG" ] ; then
    head -v $WEST_PCOORD_RETURN
fi
