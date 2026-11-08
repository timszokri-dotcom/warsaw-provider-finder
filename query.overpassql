[out:json][timeout:60];
// Q270 identifies Warsaw; use its administrative boundary rather than a radius.
area["boundary"="administrative"]["wikidata"="Q270"]["admin_level"="8"]->.warsaw;
.warsaw out tags;
nwr["shop"="car_repair"](area.warsaw);
out center tags;
