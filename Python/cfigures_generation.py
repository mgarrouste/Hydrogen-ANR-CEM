import seaborn as sns
import matplotlib.pyplot as plt
import os
import pandas as pd

interconnection = 'EI' # 'WECC', 'ERCOT', 'EI'
buildScenarios = ['reference', 'ANRElec', 'ANRElecH2'] 

years = [2030,2040,2050]

h2pathways = ['reference']
elecDemandScens = ['REFERENCE', 'HIGH', 'MEDIUM']
h2DemandScrs = ['Reference']
emssionSystems = ['NetZero', 'Negative', 'BAU']

interconnection_regions = {'EI':['MISO', 'NE', 'SERC', 'PJM', 'NY', 'SPP']}

results_figures = './Results/figures/'

from cfigures_newCapacity import create_region_column, condense_generators


def load_clean_generation_data(interconnection, buildScenario, h2pathway, elecDemScenario, h2DemandScenario, emissionSystem):
  """Loads the generation data for case
  Args:
    interconnection (str): interconnection abbreviation
    buildScenario (str): building scenario
    h2pathway (str): h2 pathway
    elecDemScenario (str): electricity demand scenario
    h2DemandScenario (str): hydrogen demand scenario
    emissionSystem (str): emission scenario
  Returns 
    df (DataFrame): data with non-zero generation with columns Year, Generator, Region, Generation (TWh)
  """
  list_df = []
  for year in years:
    results_folder = f'Results_{interconnection}_{emissionSystem}_h2Pway_{h2pathway}_{buildScenario}_True{elecDemScenario}'
    df = pd.read_csv(os.path.join(results_folder, f'{str(year)}CO2Cap0', 'CE', f'vGentechCE{str(year)}.csv'), header=0, index_col=0)
    nb_hours, nb_days = len(df), int(len(df)/24)
    sum_gen = df.sum().to_frame(name='Generation (TWh)').reset_index(names=['Generator'])
    sum_gen['Year'] = year
    sum_gen = create_region_column(sum_gen, interconnection)
    sum_gen = condense_generators(sum_gen, column='Generation (TWh)')
    sum_gen['Generation (TWh)'] *= (365/nb_days)*(24/nb_hours)/1e3 # Assume everything expressed in GWe in the output file 
    list_df.append(sum_gen)
  total_gen = pd.concat(list_df)
  return total_gen
    

def plot_generation(df, interconnection, buildScenario,h2pathway, elecDemScenario, h2DemandScenario, emissionSystem):
   # Set the style of the plot
  plt.style.use('ggplot')

  # Create figure and subplots
  fig, axes = plt.subplots(nrows=1, ncols=2, figsize=(12, 6))
    # Pivot the data for region and year
  df_region_year = df.pivot_table(values='Generation (TWh)', index='Year', columns='region', aggfunc='sum', fill_value=0)
  # Pivot the data for generator and year
  df_gen_year = df.pivot_table(values='Generation (TWh)', index='Year', columns='Generator', aggfunc='sum', fill_value=0)

    # Stacked bar plot for region
  df_region_year.plot(kind='bar', stacked=True, ax=axes[0])
  #axes[0].set_title('Capacity by Year and Region')
  axes[0].set_xlabel('Year')
  axes[0].set_ylabel('Generation (TWh)')
  axes[0].legend(title='ISO')

  # Stacked bar plot for generator
  df_gen_year.plot(kind='bar', stacked=True, ax=axes[1])
  #axes[1].set_title('Capacity by Year and Generator')
  axes[1].set_xlabel('Year')
  axes[1].set_ylabel('Generation (TWh)')
  axes[1].legend(title='Generator')

  # Adjust layout and show plot
  plt.tight_layout()
  plt.savefig(os.path.join(results_figures, f'generation_{interconnection}_{buildScenario}.png'))


if __name__ == '__main__':
  os.chdir(os.path.dirname(os.path.abspath(__file__)))
  h2pathway = 'reference'
  interconnection = 'EI'
  buildScenario = 'ANRElec'
  df = load_clean_generation_data(interconnection=interconnection, buildScenario=buildScenario, h2pathway=h2pathway, elecDemScenario='REFERENCE', h2DemandScenario='Reference',
                                  emissionSystem='NetZero')
  df.to_csv(f'./Results/data/generation_{interconnection}_{buildScenario}.csv', index=False)
  plot_generation(df, interconnection, buildScenario, h2pathway,  elecDemScenario='REFERENCE', h2DemandScenario='Reference',
                                  emissionSystem='NetZero')
