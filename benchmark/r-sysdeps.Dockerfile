# A "reasonable standard R environment": rocker/r-ver + the common system libraries that
# CRAN/Bioconductor R packages routinely need (spatial, netCDF, git2r, image, etc.). Using a
# bare rocker image penalises packages for missing *system* libs, which is an environment
# deficiency, not code decay — this base removes that confound for the decay measurement.
#
#   docker build -t lazarus/r-sysdeps:4.2.0 -f benchmark/r-sysdeps.Dockerfile .
FROM rocker/r-ver:4.2.0
RUN apt-get update && apt-get install -y --no-install-recommends \
      libnetcdf-dev libgit2-dev libgdal-dev libgeos-dev libproj-dev libudunits2-dev \
      libssl-dev libcurl4-openssl-dev libxml2-dev \
      libfontconfig1-dev libharfbuzz-dev libfribidi-dev libfreetype6-dev \
      libpng-dev libjpeg-dev libtiff5-dev libmagick++-dev \
      libglpk-dev libgmp-dev libmpfr-dev libgsl-dev libnlopt-dev libsodium-dev \
      cmake \
  && rm -rf /var/lib/apt/lists/*
