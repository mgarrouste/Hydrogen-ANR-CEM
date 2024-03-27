import seaborn as sns
import matplotlib.pyplot as plt
import os
import pandas as pd

interconnection = 'EI' # 'WECC', 'ERCOT', 'EI'
buildScenarios = ['reference', 'ANRElec', 'ANRElecH2'] 
# lTrans (limited transmission), lH2 (limited hydrogen storage), lNuclearCCS (limited nuclear and CCS)
years = [2030,2040,2050]

# TODO
h2pathways = ['reference']
elecDemandScens = ['REFERENCE', 'HIGH', 'MEDIUM']
h2DemandScrs = ['Reference']
emssionSystems = ['NetZero', 'Negative', 'BAU']

interconnection_regions = {'EI':['MISO', 'NE', 'SERC', 'PJM', 'NY', 'SPP']}

results_figures = './Results/figures/'


def get_newCapacity(interconnection, year, buildScenario):
  result_folder_path = 'Results_'+ interconnection+ '_NetZero_h2Pway_reference_'+ buildScenario+'_TrueREFERENCE'
  newCap_year_path = os.path.join(result_folder_path, str(year)+'CO2Cap0', 'CE', 'vN'+str(year)+'.csv')
  vN_df = pd.read_csv(newCap_year_path, names=['Generator', 'Capacity'])
  vN_df.dropna(inplace=True)
  vN_df = create_region_column(vN_df, interconnection)
  return vN_df

  
def create_region_column(vN_df, interconnection):
  regions = interconnection_regions[interconnection]
  def extract_iso(generator_name):
    for iso in regions:
        if iso in generator_name:
            # Return the ISO and the remaining string without the ISO part
            # This assumes there's a space character separating the ISO from the generator name
            return generator_name.replace(iso, ''), iso
    return generator_name, None
  vN_df['Generator'], vN_df['region'] = zip(*vN_df['Generator'].apply(extract_iso))
  return vN_df
   

def condense_generators(df):
  # Mark solar and wind generators with a common name
  df['Generator'] = df['Generator'].apply(lambda x: 'Solar' if 'solar' in x.lower() else x)
  df['Generator'] = df['Generator'].apply(lambda x: 'Wind' if 'wind' in x.lower() else x)
  # Drop lines if capacity == 0 
  df = df[df['Capacity'] != 0]
  # Now, group by ISO and generator_name and sum the capacities
  df = df.groupby(['region', 'Generator', 'Year'], as_index=False)['Capacity'].sum()
  return df


def plot_new_cap(df, interconnection, buildScenario):
   # Set the style of the plot
  plt.style.use('ggplot')

  # Create figure and subplots
  fig, axes = plt.subplots(nrows=1, ncols=2, figsize=(12, 6))
    # Pivot the data for region and year
  df_region_year = df.pivot_table(values='Capacity', index='Year', columns='region', aggfunc='sum', fill_value=0)
  # Pivot the data for generator and year
  df_gen_year = df.pivot_table(values='Capacity', index='Year', columns='Generator', aggfunc='sum', fill_value=0)

    # Stacked bar plot for region
  df_region_year.plot(kind='bar', stacked=True, ax=axes[0])
  #axes[0].set_title('Capacity by Year and Region')
  axes[0].set_xlabel('Year')
  axes[0].set_ylabel('Capacity (GWe)')
  axes[0].legend(title='ISO')

  # Stacked bar plot for generator
  df_gen_year.plot(kind='bar', stacked=True, ax=axes[1])
  #axes[1].set_title('Capacity by Year and Generator')
  axes[1].set_xlabel('Year')
  axes[1].set_ylabel('Capacity (GWe)')
  axes[1].legend(title='Generator')

  # Adjust layout and show plot
  plt.tight_layout()
  plt.savefig(os.path.join(results_figures, f'new_capacity_{interconnection}_{buildScenario}.png'))

def test():
  os.chdir(os.path.dirname(os.path.abspath(__file__)))
  get_newCapacity('EI', '2030', 'ANRElec')

def main():
  os.chdir(os.path.dirname(os.path.abspath(__file__)))
  interconnection = 'EI'
  buildScenario = 'ANRElec'
  list_df = []
  for year in years:
     year_df = get_newCapacity(interconnection, year, buildScenario)
     year_df['Year'] = year
     list_df.append(year_df)
  total_df = pd.concat(list_df)
  total_df = condense_generators(total_df)
  plot_new_cap(total_df, interconnection, buildScenario)


if __name__ == '__main__':
  main()
  #test()