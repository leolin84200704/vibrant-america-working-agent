#!/bin/bash
# usage: gql.sh file.json   (body {query, variables})
D=$(dirname "$0"); T=$(node $D/mint.js)
curl -s https://api.vibrant-america.com/v2/portal/trans-service/graphql -H 'content-type: application/json' -H "authorization: Bearer $T" --data @"$1"
