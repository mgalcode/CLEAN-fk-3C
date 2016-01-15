# Control script for CLEAN-fk-3c
#    by Martin Gal
#    2016 - Jan - 15
#
# Python modules needed:
# Obspy, numpy,scipy, matplotlib
#
#
#
# functions used:
# ---------------
# read                   ... obspy read function
# get_metadata           ... reads metadata from standard iris output
# equalize               ... checks if there are equal amout of traces and if all stations are in the correct order
# metric_mseed           ... generates coordinates for the stations
# remove_gain            ... removes gain, i.e. conversion to m/s
# PSAR_dict()            ... azimuth for BH1 component of PSAR, returns dictionary with station name and angle
# make_subwindows_PSAR   ... makes subwindows with data, mean removed and Hann taper applied
# make_csdm              ... generates the cross spectral density matrix
# CLEAN_3C_Capon         ... CLEAN procedure
# np.linalg.inv          ... numpy routine to get inverse matrix
# make_P_Capon           ... 3 component beamformer
# get_max                ... extracts maxima of strongest source on each component
# make_plot              ... Plots the beamforming results

# variables used:
# ---------------
# nsamp          ... amount of data points in a temporal subwindow
# smin           ... minimum slowness that is used to perform the slowness search [s/deg]
# smax           ... max slowness. values -50 and 50 are standard for these smin and smax
# sinc           ... the increment of the slowness. the lower the more accurate the finer the grid-search is. default value should be 0.5
# find           ... frequency at which the DOA is performed. warning: it is not [Hz]. It connected to the frequency by the equation freq = find/(nsamp*dt)
#                    where freq is in [Hz]. 
# fave           ... frequency to average over. Do not use more than 5% of find, otherwise your results can be biased in the velocity estimation.
# control        ... control parameter that extracts power (between 0-1). 0.1 is default 
# cln_iter       ... number of iterations for the CLEAN algo, set at 0, you get the normal 3C beamforming result. Set a higher value to clean spectrum.
#                    for CLEAN, try 30 and go from there depending on what you would like to achieve.
# show_peak_info ... information about peaks from which energy is removed, works for cln_iter > 0, 
#                    energy is removed from 3 components, hence there will be 3 peaks removed per iteration.
# st             ... matrix of Z data. first element is sensor station and second element is time series. dimensions are st[nr][nsamp]
# st0            ... North-South component, can also be BH1
# st1            ... East-West component or BH2
# folder         ... path to metadata directory
# meta_f         ... full path to metadata file
# dic_meta       ... dictionary with station name/location information
# nr             ... amount of array stations/sensors
# rx             ... vector of r_x component for all stations. rx is in [deg]. reference station of the array is always first sensor in the sequence.
# ry             ... vector of r_y component ..
# nwin           ... amount of time windows that need to be extracted from the time series
# dt             ... time steps. dependent on array.
# freq           ... frequency at which the DOA is performed in [Hz]
# df             ... averaging frequency
# kmin           ... minimum wavenumber. it is used later for the calculation as all angles need to be considered of the arriving signal.
#                    the steering vector is basically exp(ikr) where r is the interstation distance in [deg].
# kmax           ... max wavenumber
# kinc           ... wavenumber increment
# nk             ... amount of slowness steps/ respectively wavenumber steps from min to ma
# pdic           ... dictionary with BH1 azimuth directions. (this is made specifically for the philbara array /PSAR)
# xt             ... data split into temporal subwindows, mean removed and Hann taper applied.
# csdm           ... cross spectral density matrix
# icsdm          ... inverse csdm
# fk_cln         ... clean power spectrum 
# polariz        ... power output for Z,R,T component
# max_c          ... xy-slowness of stronges source in polariz [s/deg,s/deg]x3
# max_o          ... power of strongest source in polariz 
# tt1, tt2, tt3  ... clean + background spectra for all 3 components
# Z,R,T          ... normalized power components [dB]

import numpy as np
from obspy import read
from subroutine_CLEAN_3c import *


nsamp          = 8000 
smin           = -40.0
smax           = 40.0
sinc           = 0.5
find           = 60
fave           = 3
control        = 0.1
cln_iter       = 0
show_peak_info = True




st  = read('/Users/mgal/temp_SETA/3comp/2006.315*BHZ.SAC')
st0 = read('/Users/mgal/temp_SETA/3comp/2006.315*BHN.SAC')
st1 = read('/Users/mgal/temp_SETA/3comp/2006.315*BHE.SAC') 


st,st0,st1 = equalize(st,st0,st1)
nr = st0.count()
rx,ry = get_rxy_sac(nr,st0)   

# remove gain if known and response is flat in the frequency range of interest
st, st0, st1 = remove_gain(st,st0,st1,nr,gain=1)


nwin = int(st0[0].count()/nsamp)*2-1
dt = st0[0].stats.delta
freq = find/(nsamp*dt)
kmin = smin*freq
kmax = smax*freq
kinc = sinc*freq
nk = int(((kmax-kmin)/kinc+0.5)+1) 

print 'number of nwin:',nwin
print 'npts:',st0[0].count()
print 'Amount of stations:', nr
print 'CLEAN-Capon-3C DOA estimation is performed at:','freq',freq,'+-',fave/float(nsamp*dt)

pdic = PSAR_dict()
xt = make_subwindows(nr,nwin,st,st0,st1,nsamp)
csdm = make_csdm(nwin,nr,xt,nsamp,find,fave)
icsdm = np.zeros((3,3*nr,3*nr),dtype=complex)
fk_cln = np.zeros((3,nk,nk))

for cln in range(cln_iter+1):
    if cln != 0:
        csdm,fk_cln = CLEAN_3C_Capon(nr,max_c,smin,sinc,freq,rx,ry,csdm,control,fk_cln,cln,nk,show_peak_info)   
    for k in range(3):
        icsdm[k] = np.linalg.inv(csdm[k]) 
    polariz = make_P_Capon(nk,nr,kinc,kmin,rx,ry,icsdm)
    max_c, max_o = get_max(polariz,smin,sinc,cln)

tt1 = (fk_cln[0] + polariz[:,:,0] )
tt2 = (fk_cln[1] + polariz[:,:,1] )
tt3 = (fk_cln[2] + polariz[:,:,2] )

Z = (tt1/tt1.max())
R = (tt2/tt2.max())
T = (tt3/tt3.max())

print '-------------------------'
print 'Power info for strongest source:'
print 'Total   %.02f dB'%(10*np.log10((tt1+tt2+tt3).max()))
print 'Z-comp  %.02f dB'%(10*np.log10(tt1.max()))
print 'R-comp  %.02f dB'%(10*np.log10(tt2.max()))
print 'T-comp  %.02f dB'%(10*np.log10(tt3.max()))
print '-------------------------'

make_plot(Z,R,T,smin,smax)







