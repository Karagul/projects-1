
import datetime
import pandas as pd
import numpy as np
from pandas_datareader import data as da
import bt


"""
Inputs
*********************************************************************************************************
"""
File1= "/Users/jsce/Documents/Hult/MFIN/Analytics/Project/Financials for Python/apple2019.csv"
Ticker = 'aapl'
CreateFile=False
FileExit= "/Users/jsce/Documents/Hult/MFIN/Analytics/Project/Vodafone.csv"

LTGR=0.035

#create a list of indexes for the dataframe to fill
index=['Y1','Y2','Y3','Y4','Y5']

#Financial Statements
FS=pd.read_csv(File1,index_col="Titles")
index_column=FS.index.values.tolist()
#format Financial Statements
FS = FS.apply (pd.to_numeric, errors='coerce')
FS=FS.fillna(0)
"""
End of Inputs
*********************************************************************************************************
"""

"""
Previous FCF
*********************************************************************************************************
"""
def prevFCF():

    #revenue=FS.loc['Total Revenue']
    grossprofit=FS.loc['Total Gross Profit']
    #cogs=revenue-grossprofit
    
    if 'Total Selling, General and Administrative Expenses' not in index_column:
        sga=FS.loc['Selling, General and Administrative Expenses']
    else:
        sga=FS.loc['Total Selling, General and Administrative Expenses']
    
    rd=FS.loc['Research and Development Expenses']
    depreciation=FS.loc['Depreciation, Amortization and Depletion, Non-Cash Adjustment']
    
    operatingexpenses=sga+rd+depreciation*0
    
    #Operating profit before taxes
    opbt=grossprofit-operatingexpenses
    #Tax rate
    TaxExpense=FS.loc['Provision for Income Tax']
    
    #Extract values from dataframe
    nopat=opbt-TaxExpense
    
    capex=FS.loc['Capital Expenditure (Calc)']
    
    #Calculate Change in Working Capital
    WorkingCapital=FS.loc['Total Changes in Operating Capital']

    #Create FCF
    FCF=(nopat+depreciation-capex+WorkingCapital).iloc[::-1]
    #return FCF
    return (FCF)
"""
End of Previous FCF
*********************************************************************************************************
"""

"""
WACC
*********************************************************************************************************
"""
#Market Return
def MktReturn():
    #one year ago
    OneYearAgo= datetime.datetime.now() - datetime.timedelta(days=365)
    #Get data from the market
    mktdata = bt.get('^GSPC',start=OneYearAgo)
    #Calculate Return of the market
    start=mktdata.gspc[0]
    end=mktdata.gspc[-1]
    Return=end/start-1

    return Return

#Risk Free Rate
def RiskFree():

   from datetime import timedelta

   adate=datetime.datetime.now()
   adate -= timedelta(days=1)
   while adate.weekday() > 4: # Mon-Fri are 0-4
       adate -= timedelta(days=1)

   rfrdf=bt.get('^IRX',start=adate)/100
   rfr=rfrdf.iloc[-1,-1]
   return rfr

#Beta
def Calc_Beta(Ticker):
    #one year ago
    OneYearAgo= datetime.datetime.now() - datetime.timedelta(days=365)
    #Get data from the market
    df=bt.get(Ticker,start=OneYearAgo).pct_change()
    df=df.dropna()
    mkt=bt.get('^GSPC',start=OneYearAgo).pct_change()
    mkt=mkt.dropna()
    df['gspc']=mkt.gspc
    df=df.dropna()
    np_array = df.values
    m = np_array[:,0] # market returns are column zero from numpy array
    s = np_array[:,1] # stock returns are column one from numpy array
    covariance = np.cov(s,m) # Calculate covariance between stock and market
    Beta = covariance[0,1]/covariance[1,1]
    return Beta

#Tax rate
def TaxRate():
    
    #Extract values from dataframe
    TaxExpense=FS.loc['Provision for Income Tax']
    PreTaxIncome=FS.loc['Pretax Income']
    #Calculate Tax rate
    
    T=TaxExpense/PreTaxIncome
    for i in T.index:
        if T[i]>0.25:
            T[i]=0.25
        elif T[i]<0:
            T[i]=0
    T=T.iloc[::-1].mean()

    
    
    return T    
#Cost of Debt
def CostofDebt():

    #Extract values from dataframe
    InterestExpense=FS.loc['Interest Expense Net of Capitalized Interest']
    debt=FS.loc['Total Debt']
    #Calculate Tax rate
    I=InterestExpense/debt
    I=I.iloc[::-1]
    I=I.iloc[-1]
    return I

#WACC
def WACC(StockTicker):
    #Get Market Cap for market value of Equity
    E=da.get_quote_yahoo(StockTicker)['marketCap']
    #Obtain components for CAPM for Ke
    Beta=Calc_Beta(StockTicker)
    Rf=RiskFree()
    MR=MktReturn()
    MRP=MR-Rf
    #Calculate Ke
    Ke=Rf+Beta*MRP
    #Value of Debt
    D=FS.loc['Total Debt']
    D=D.iloc[0]*1000
    #Cost of Debt
    Kd=CostofDebt()
    #Tax Rate
    T=TaxRate()

    WACC = ((E/(D+E))*Ke)+((D/(D+E))*Kd*(1-T))
    WACC = WACC.iloc[-1]
    return WACC

"""
END OF WACC
*********************************************************************************************************
"""


"""
CALCULATION OF FREE CASH FLOWS FOR PROJECTED YEARS
*********************************************************************************************************
"""
#Current Free Cash Flow
def FreeCashFlow():
    
    
    """
    This section will get historic revenue, get the average growth %
    Calculate future growth until long term growth rate, and
    Estimate revenue for projected years
    """
    
    
    #Get Revenue from file for historic years
    revenue=FS.loc['Total Revenue'].iloc[::-1]
    #Revenue percentage change
    revpct=revenue.pct_change().dropna()
    #get Average revenue growth
    revavg=revpct.mean()

    revgrowth=pd.DataFrame(columns=['Revenue Growth %']) #create empty dataframe for revenue growth
    
    #Populate dataframe of revenue growth with a loop for all values of the index
    counter=1 #counter for difference division on years 1 to 4
    for i in index:
        if i=='Y1':
            revgrowth.loc[i] = revavg-((revavg-LTGR)/(6-counter)) #first year growth %
            x=revgrowth.loc[i] #set variable as current year value to use in next year calculation
        elif i!= 'Y5':
            revgrowth.loc[i]= x-((x-LTGR)/(6-counter)) #revenue growth years 2 to 4
            x=revgrowth.loc[i] #set variable as current year value to use in next year calculation
        else:
            revgrowth.loc[i] =  LTGR #Revenue growth final year
        counter=counter+1#move counter for next year

    #Revenue projections
    projrev = pd.DataFrame(columns=['Revenue'])
    counter=0
    for i in index:
        if i=='Y1':
            projrev.loc[i] = revenue[-1]*(1+revgrowth.iloc[counter]['Revenue Growth %']) #first year projected revenue
            x=projrev.loc[i] #set variable as current year value to use in next year calculation
        else:
            projrev.loc[i]= x*(1+revgrowth.iloc[counter]['Revenue Growth %'])#revenue projection years 2 to 5
            x=projrev.loc[i] #set variable as current year value to use in next year calculation
        counter=counter+1#move counter for next year
        
        """
        End of the section
        """
        

    """
    This section calculates COGS, SG&A, R&D, Depreciation & Amortization and CAPEX as a percentage of sales for future years
    The calculation will the moving average of the last 3 years as a percentage of sales
    """
    #Get gross profit from file
    grossprofit=FS.loc['Total Gross Profit']
    cogs=(revenue-grossprofit)
    #COGS as percentage of sales
    cogspctsales=(cogs/revenue)
    
    #dataframe to fill up with projected years with moving average
    projcogspct=pd.DataFrame(columns=['COGS as % of sales'])
    for i in index:
        if i=='Y1':
            x=cogspctsales[-3]
            y=cogspctsales[-2]
            z=cogspctsales[-1] 
        
        elif i=='Y2':
            x=cogspctsales[-2]
            y=cogspctsales[-1]
            z=projcogspct.iloc[-1]
        
        elif i=='Y3':
            x=cogspctsales[-1]
            y=projcogspct.iloc[-2]
            z=projcogspct.iloc[-1]
        else:
            x=projcogspct.iloc[-3]
            y=projcogspct.iloc[-2]
            z=projcogspct.iloc[-1]
        
        projcogspct.loc[i] = (x+y+z)/3


    #Get SG&A from file
    if 'Total Selling, General and Administrative Expenses' not in index_column:
        sga=FS.loc['Selling, General and Administrative Expenses']
    else:
        sga=FS.loc['Total Selling, General and Administrative Expenses']
    #SG&A as percentage of sales
    sgapctsales=(sga/revenue)
    
    #dataframe to fill up with projected years with moving average
    projsgapct=pd.DataFrame(columns=['SG&A as % of sales'])
    for i in index:
        if i=='Y1':
            x=sgapctsales[-3]
            y=sgapctsales[-2]
            z=sgapctsales[-1] 
        
        elif i=='Y2':
            x=sgapctsales[-2]
            y=sgapctsales[-1]
            z=projsgapct.iloc[-1]
        
        elif i=='Y3':
            x=sgapctsales[-1]
            y=projsgapct.iloc[-2]
            z=projsgapct.iloc[-1]
        else:
            x=projsgapct.iloc[-3]
            y=projsgapct.iloc[-2]
            z=projsgapct.iloc[-1]
        
        projsgapct.loc[i] = (x+y+z)/3


    #R&D as percentage of sales
    rd=FS.loc['Research and Development Expenses']
    rdpctsales=(rd/revenue)
    
    #dataframe to fill up with projected years with moving average
    projrdpct=pd.DataFrame(columns=['R&D as % of sales'])
    for i in index:
        if i=='Y1':
            x=rdpctsales[-3]
            y=rdpctsales[-2]
            z=rdpctsales[-1] 
        
        elif i=='Y2':
            x=rdpctsales[-2]
            y=rdpctsales[-1]
            z=projrdpct.iloc[-1]
            
        elif i=='Y3':
            x=rdpctsales[-1]
            y=projrdpct.iloc[-2]
            z=projrdpct.iloc[-1]
        else:
            x=projrdpct.iloc[-3]
            y=projrdpct.iloc[-2]
            z=projrdpct.iloc[-1]
        
        projrdpct.loc[i] = (x+y+z)/3


    #Depreciation and amortization as percentage of sales
    depreciation=FS.loc['Depreciation, Amortization and Depletion, Non-Cash Adjustment']
    deppctsales=(depreciation/revenue)

    projdeppct=pd.DataFrame(columns=['Depreciation as % of sales'])
    for i in index:
        if i=='Y1':
            x=deppctsales[-3]
            y=deppctsales[-2]
            z=deppctsales[-1] 

        elif i=='Y2':
            x=deppctsales[-2]
            y=deppctsales[-1]
            z=projdeppct.iloc[-1]
        
        elif i=='Y3':
            x=deppctsales[-1]
            y=projdeppct.iloc[-2]
            z=projdeppct.iloc[-1]
        else:
            x=projdeppct.iloc[-3]
            y=projdeppct.iloc[-2]
            z=projdeppct.iloc[-1]
        
        projdeppct.loc[i] = (x+y+z)/3

    #CAPEX as percentage of sales
    capex=FS.loc['Capital Expenditure (Calc)']
    capexpctsales=(capex/revenue)
    
    projcapexpct=pd.DataFrame(columns=['CAPEX as % of sales'])
    for i in index:
        if i=='Y1':
            w=capexpctsales[-4]
            x=capexpctsales[-3]
            y=capexpctsales[-2]
            z=capexpctsales[-1]
        elif i=='Y2':
            w=capexpctsales[-3]
            x=capexpctsales[-2]
            y=capexpctsales[-1]
            z=projcapexpct.iloc[-1]
        elif i=='Y3':
            w=capexpctsales[-2]
            x=capexpctsales[-1]
            y=projcapexpct.iloc[-2]
            z=projcapexpct.iloc[-1]
        elif i=='Y4':
            w=capexpctsales[-1]
            x=projcapexpct.iloc[-3]
            y=projcapexpct.iloc[-2]
            z=projcapexpct.iloc[-1]
        else:
            w=projcapexpct.iloc[-4]
            x=projcapexpct.iloc[-3]
            y=projcapexpct.iloc[-2]
            z=projcapexpct.iloc[-1]
    
        projcapexpct.loc[i] = (w+x+y+z)/4
   
    """
    End of the section
    """



    """
    NET OPERATING WORKING CAPITAL
    """

    #Get current assets from file
    currentassets=FS.loc['Total Current Assets']
    curasspctsales=(currentassets/revenue).iloc[[-3,-2,-1]].mean()#Mean of current assets as a percentage of sales


    #Get current liabilities from file
    currentliabilities=FS.loc['Total Current Liabilities']
    curliabpctsales=(currentliabilities/revenue).iloc[[-3,-2,-1]].mean()#Mean of current liabilities as a percentage of COGS

    
    WC=pd.DataFrame(columns=['Revenue'])
    WC['Revenue']=projrev['Revenue']
    WC['CurrentAssets']=WC.Revenue*curasspctsales
    WC['CurrentLiabilities']=WC.Revenue*curliabpctsales
    WC['Working Capital']=WC.CurrentAssets-WC.CurrentLiabilities

    WC=WC['Working Capital'].iloc[::-1]
    WC.loc['Y0'] = currentassets.iloc[0]-currentliabilities.iloc[0]
    WC=WC.iloc[::-1].diff().dropna()*(-1)
           
    WorkingCapital=(FS.loc['Total Changes in Operating Capital']/revenue).iloc[::-1].mean()*(-1)

    """
    End of the Section
    """       


    #Get Average Tax rate
    
    #Extract values from dataframe
    TaxExpense=FS.loc['Provision for Income Tax']
    PreTaxIncome=FS.loc['Pretax Income']
    #Calculate Tax rate
    T=TaxExpense/PreTaxIncome
    for i in T.index:
        if T[i]>0.25:
            T[i]=0.25
        elif T[i]<0:
            T[i]=0
            
    T=T.iloc[::-1].mean()
    

    """
    In this section we will make FCF for projected years
    """
    FCF=pd.DataFrame(columns=['Revenue'])
    #Build dataframe with FCF starting with projected revenue
    FCF['Revenue']=projrev['Revenue']
    #Add COGS as % of sales
    FCF['COGSpct']=projcogspct['COGS as % of sales']
    #Find and add COGS
    FCF['COGS']=FCF.Revenue*FCF.COGSpct
    #Get Gross Profit
    FCF['GrossProfit']=FCF.Revenue-FCF.COGS
    #Add SG&A as % of sales
    FCF['SGApct']=projsgapct['SG&A as % of sales']
    #Calculate and add SG&A
    FCF['SGA']=FCF.Revenue*FCF.SGApct
    #Add R&D as % of sales
    FCF['RDpct']=projrdpct['R&D as % of sales']
    #Calculate and add R&D
    FCF['RD']=FCF.Revenue*FCF.RDpct
    #Add Depreciation as % of sales
    FCF['DEPpct']=projdeppct['Depreciation as % of sales']
    #Calculate and add Depreciation
    FCF['DEP']=FCF.Revenue*FCF.DEPpct
    #Add Operating Expenses
    FCF['OperatingExpenses']=FCF.SGA+FCF.RD+FCF.DEP*0
    #Calculate and add Operating Profit Before Taxes
    FCF['OperatingProfitBeforeTaxes']=FCF.GrossProfit-FCF.OperatingExpenses
    #Calculate Taxes
    FCF['Taxes']=FCF.OperatingProfitBeforeTaxes*T
    #Calculate and add NOPAT
    FCF['NOPAT']=FCF.OperatingProfitBeforeTaxes-FCF.Taxes
    #Calculate CAPEX as % of sales
    FCF['CAPEXpct']=projcapexpct['CAPEX as % of sales']
    FCF['CAPEX']=FCF.Revenue*FCF.CAPEXpct
    #Calculate NOWC
    x=FCF.Revenue*WorkingCapital
    if x[-1]>WC[-1]:
        FCF['NOWC']=x
    else:
        FCF['NOWC']=WC
    FCF['FreeCashFlow']=FCF.NOPAT+FCF.DEP-FCF.CAPEX+FCF.NOWC
    """
    End of the Section
    """
    return (FCF)

"""
*********************************************************************************************************
END OF CALCULATION OF FREE CASH FLOWS FOR PROJECTED YEARS
"""

"""
Calculation of Terminal Value
*********************************************************************************************************
"""
def TerminalValue(Ti):
    
    
    EndCAPEX=FreeCashFlow().iloc[-1]['CAPEX']
    if FreeCashFlow().iloc[-1]['CAPEXpct']/2<0.05:
        EndCAPEX=FreeCashFlow().iloc[-1]['CAPEX']/2
    else:
        EndCAPEX=0.05*FreeCashFlow().iloc[-1]['Revenue']
    
    TV=(FreeCashFlow().iloc[-1]['FreeCashFlow']+EndCAPEX)*(1+LTGR)/(WACC(Ti)-LTGR)
    TerminalValue=pd.DataFrame(columns=['Terminal Value'])
    
    for i in index:
        if i!='Y5':
            TerminalValue.loc[i]=0
        else:
            TerminalValue.loc[i]=TV
    
    return TerminalValue
    
def EV(Ti):
    FinalFCF=pd.DataFrame()
    FinalFCF=FreeCashFlow().loc[:,'FreeCashFlow'].to_frame()
    FinalFCF['TerminalValue']=TerminalValue(Ti)['Terminal Value']
    FinalFCF['ToDiscountFlows']=FinalFCF.FreeCashFlow+FinalFCF.TerminalValue
    
    PresentValueList=FinalFCF['ToDiscountFlows']
    EnterpriseValue=np.npv(WACC(Ti),PresentValueList)
    
    return EnterpriseValue
    
def EquityValue(Ti):
    
    debt=FS.loc['Total Debt'][0]
    Cash=FS.loc['Total Cash and Cash Equivalents, End of Period'][0]
    EquityValue=EV(Ti)-debt+Cash
    
    
    return EquityValue

def ImpliedStockPrice(Ti):
    Shares=da.get_quote_yahoo(Ti)['sharesOutstanding']
    Price=EquityValue(Ti)*1000/Shares
    
    return Price



y=ImpliedStockPrice(Ticker).iloc[-1]
today=datetime.datetime.now()
mktdata = bt.get(Ticker,start='2019-12-05')
st=mktdata.iloc[-1,-1]
diff=y/st-1
pctdiff= "%.2f%%" % (100 * diff)



print('The implied stock price is '+str("%.2f" % y))
print('The market stock price is '+str("%.2f" %st))
print('There is a difference of '+pctdiff)

if CreateFile==True:
    FreeCashFlow().transpose().to_csv(FileExit)
    
    