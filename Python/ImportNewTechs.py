# Michael Craig
# October 4, 2016
# Function imports data for new technologies eligible for construction in capacity expansion model

import os, pandas as pd
from AuxFuncs import *
from SetupGeneratorFleet import *

def getNewTechs(regElig, regCostFrac, currYear, incITC, stoInCE, seasStoInCE, fuelPrices, yearIncDACS, coOptH2,
                incNuc, transRegions, contFlexInelig, buildScen, onlyNSPSUnits=True, allowCoalWithoutCCS=False, firstYearForCCS=2030):
    currYear2 = currYear
    if currYear > 2050: currYear = 2050
    # Read in new techs and add parameters
    if not coOptH2:
        newTechsCE = pd.read_excel(os.path.join('Data', 'NewPlantData', 'NewTechFrameworkOriginal.xlsx'))
    elif coOptH2:
        if buildScen == 'ANRElec':
            newTechsCE = pd.read_excel(os.path.join('Data', 'NewPlantData', 'NewTechFramework_ANRElec.xlsx'))
        elif buildScen == 'ANRElecH2':
            newTechsCE = pd.read_excel(os.path.join('Data', 'NewPlantData', 'NewTechFramework_ANRElecH2.xlsx'))
        else:
            newTechsCE = pd.read_excel(os.path.join('Data', 'NewPlantData', 'NewTechFramework.xlsx'))
    newTechsCE = inputValuesForCurrentYear(newTechsCE, 'Data\\NewPlantData', currYear)
    newTechsCE = addUnitCommitmentParameters(newTechsCE, 'PhorumUCParameters.csv')
    newTechsCE = addUnitCommitmentParameters(newTechsCE, 'StorageUCParameters.csv')
    newTechsCE = addFuelPrices(newTechsCE, currYear, fuelPrices)
    if currYear2 >= yearIncDACS: newTechsCE = addDACS(newTechsCE, fuelPrices, currYear)
    newTechsCE = addRandomOpCostAdder(newTechsCE)
    newTechsCE = calcOpCost(newTechsCE)
    newTechsCE = addRegResCostAndElig(newTechsCE, regElig, regCostFrac)
    newTechsCE = addReserveEligibility(newTechsCE, contFlexInelig)
    # Discount costs
    for c, l in zip(['CAPEX(2012$/MW)', 'FOM(2012$/MW/yr)'], ['occ', 'fom']):
        newTechsCE[c] = convertCostToTgtYr(l, newTechsCE[c])
    # Filter plants
    if not allowCoalWithoutCCS: newTechsCE = newTechsCE.loc[newTechsCE['PlantType'] != 'Coal Steam']
    if onlyNSPSUnits: newTechsCE = newTechsCE.loc[newTechsCE['NSPSCompliant'] == 'Yes']
    if not stoInCE: newTechsCE = newTechsCE.loc[newTechsCE['FuelType'] != 'Energy Storage']
    if not seasStoInCE: newTechsCE = newTechsCE.loc[newTechsCE['PlantType'] != 'Hydrogen']
    if not incNuc: newTechsCE = newTechsCE.loc[newTechsCE['PlantType'] != 'Nuclear']
    if currYear < firstYearForCCS: newTechsCE = newTechsCE.loc[~newTechsCE['PlantType'].str.contains('CCS')]
    # Include ITC
    if incITC:
        newTechsCE = modRECapCostForITC(newTechsCE, currYear, buildScen)
    # Assign tech options to each region
    newTechsCE = repeatNonRETechOptionsForEachRegion(newTechsCE, transRegions)
    newTechsCE.reset_index(inplace=True, drop=True)
    return newTechsCE

def inputValuesForCurrentYear(newTechsCE, newPlantDataDir, currYear):
    if currYear > 2050: currYear = 2050
    inputFiles = newTechsCE['DataSource'].unique()
    for inputFile in inputFiles:
        # Load annual new plant data and get column #s of 2d list
        annualData = readCSVto2dList(os.path.join(newPlantDataDir, inputFile + '.csv'))
        (forecastTechCol, forecastParamCol) = (annualData[0].index('PlantType'), annualData[0].index('Parameter'))
        yearCol = annualData[0].index(str(currYear)) if str(currYear) in annualData[0] else len(annualData[0])-1
        # Input data into new plant df
        for row in annualData[1:]: newTechsCE.loc[newTechsCE['PlantType']==row[forecastTechCol], row[forecastParamCol]] = float(row[yearCol])
    return newTechsCE

# Add DACS parameters to new techs. DACS gen & capac values are negative in optim, so
# all cost values (op, fom, cap) are negative (so that gen or cap * cost = positive) and emission rate is
# positive (so that gen * ER = negative). Data based on Keith's Joule paper.
def addDACS(newTechsCE, fuelPrices, currYear):
    if currYear > 2050: currYear = 2050
    dacsCap = -500
    # CO2 ems removal rate NET of emissions from NG for heat.
    # Keith: 1 t CO2 removal requires 366 kWh e [burned 5.25 GJ NG is also captured; not included in 1 t co2]
    # 1 t co2/366 kwh * 2000 lb/t * 1000 kwh/mwh * mwh/3.412 mmbtu = 1601.5 lb CO2/MMBtu
    # If include heat, 1 t co2/(366 kwh + 5.25gj * .277 mwh/gj * 1000 kwh/mwh) = 1 t co2/1820.25 kwh
    #               1 t co2/1820.25 kwh * 2000lb/t * 1000kwh/mwh * mwh/3.412 mmbtu = 322 lb co2/mmbtu
    # Realmonte: 1 t CO2 removed per 500 kWh e (given as 1.8 GJ electricity, 1 GJ = 0.27778 MWh) (also 8.1 GJ heat)
    # 1 t co2/1.8 gj * gj/.277 mwh * mwh/1000 kwh * 2000 lb/t * 1000 kwh/mwh * mwh/3.412 mmbtu = 1172.3 lb co2/mmbtu
    dacsNetEmsRate = 322  # lb CO2/MMBtu ; 1601.5 for keith, 1172.3 for realmonte, 322 for keith w/ NG heat
    dacsHR = 3412  # btu/kWh; just conversion factor
    # Set op costs as VOM because HR is not an accurate value
    vom = 26/366*1000  # $/MWh; Keith gives $26/t CO2; instead use $26/366 kWh
    fuelPrices = fuelPrices.loc[currYear] if currYear in fuelPrices.index else fuelPrices.iloc[-1]
    fuelPrices = convertCostToTgtYr('fuel', fuelPrices)
    ngPrice = fuelPrices['Natural Gas']   
    natGasCost = ngPrice * 5.25/366 * 1000 * 0.947  # $/MWh; 5.25 GJ NG/366 kwh given in Keith; * ng price ($/mmbtu) * conversions
    totalOpCost = natGasCost + vom
    capCost = 779.5*1e6/40.945  # 2086000000/40.945  # 779.5*1e6/40.945 #$779.5M buys 0.98Mt co2/yr; @ 366kwh/1 t co2, that is 0.98*366*1e6/8760 = 40.945 MW
    # Add row to new techs df
    newRow = {'PlantType': ['DAC'], 'DataSource': ['handCalc'], 'FuelType': ['DAC'], 'Capacity (MW)': [dacsCap],
              'Heat Rate (Btu/kWh)': [dacsHR], 'CAPEX(2012$/MW)': [-capCost], 'FOM(2012$/MW/yr)': [0], 'VOM(2012$/MWh)': [-totalOpCost],
              'NSPSCompliant': ['Yes'], 'CO2EmRate(lb/MMBtu)': [dacsNetEmsRate], 'Lifetime(years)': [30],
              'FuelPrice($/MMBtu)': [0], 'RampRate(MW/hr)': [abs(dacsCap)], 'MinLoad(MWh)': 0, 'MinDownTime(hrs)': 0, 'StartCost($)': 0}
    newTechsCE = pd.concat([newTechsCE, pd.DataFrame(newRow)])
    newTechsCE.reset_index(drop=True, inplace=True)
    return newTechsCE

# For each non-wind & non-solar tech option, repeat per region. (New W&S use lat/long coords later.)
def repeatNonRETechOptionsForEachRegion(newTechsCE, transRegions):
    newTechsRE = newTechsCE.loc[newTechsCE['PlantType'].isin(['Wind', 'Solar PV'])].copy()
    newTechsNotRE = newTechsCE.loc[~newTechsCE.index.isin(newTechsRE.index)].copy()
    l = [newTechsRE]
    for r in transRegions:
        regionTechs = newTechsNotRE.loc[~newTechsNotRE['PlantType'].isin(['Wind', 'Solar PV'])].copy()
        regionTechs['region'] = r
        l.append(regionTechs)
    return pd.concat(l)

# Account for ITC in RE cap costs
# http://programs.dsireusa.org/system/program/detail/658
def modRECapCostForITC(newTechsCE, currYear, buildScen):
    """Modifying capital costs to include ITC after implementation year
    Args:
        - newTechsCE (DataFrame): new technologies data
        - currYear (int): year considered
        - buildScen (str): building scenario
    Returns:
        - newTechsCE (DataFrame): new technologies data with ITC applied to relevant capital costs
    """
    if currYear > 2050: currYear = 2050
    windItc, windItcYear = .21, 2020  # wind ITC expires at 2020; .21 is average of 2016-2019 ITCs
    solarItcInit, solarItcIndef, solarItcYear = .3, .1, 2020  # solar ITC doesn't expire, but goes from .3 to .1
    anrh2Itc, anrh2ItcYear = 0.3, 2100 # ITC for ANR-H2 does not expire
    anrItc, anrItcYear = 0.3, 2100 # ITC for ANRs does not expire
    if currYear <= windItcYear: newTechsCE = modRECost(newTechsCE, windItc, 'Wind')
    if currYear <= solarItcYear: newTechsCE = modRECost(newTechsCE, solarItcInit, 'Solar PV')
    else: newTechsCE = modRECost(newTechsCE, solarItcIndef, 'Solar PV')
    if 'ANRElec' in buildScen:
        if currYear <= anrItcYear:
            for plantType in ['iPWR', 'HTGR', 'PBRHTGR', 'iMSR', 'Micro']:
                newTechsCE = modRECost(newTechsCE, anrItc, plantType)
        if 'H2' in buildScen:
            if currYear <= anrh2ItcYear: 
                for plantType in ['iPWRHTSE', 'HTGRHTSE', 'PBRHTGRHTSE', 'iMSRHTSE', 'MicroHTSE']:
                    newTechsCE = modRECost(newTechsCE, anrh2Itc, plantType)
    return newTechsCE
    
def modRECost(newTechsCE, itc, plantType):
    """Modifying capital costs to include ITC for a plant type
    Args:
        - newTechsCE (DataFrame): new technologies data
        - itc (float): value of the investment tax credit
        - plantType (str): plant type to apply the itc to, must be in the newTechsCE 
    Returns:
        - newTechsCE (DataFrame): new technologies data with ITC applied to the plantType
    """
    newTechsCE = newTechsCE.set_index('PlantType')
    newTechsCE.loc[plantType, 'CAPEX(2012$/MW)'] *=(1-itc)
    newTechsCE.reset_index(inplace=True)
    return newTechsCE
    
