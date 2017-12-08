"""This model is the rat flea human with seasonality model made to be fitted against mortality data"""
import pymc as pm
import numpy as np
import pandas as pd
from datetime import date
from tools.TempReader import TempReader


__all__ = ['confirmed_cases', 'rat_pop', 'beta_h', 'gamma_h', 'p_recovery_h', 'temp_scale', 'beta_r', 'gamma_r',
           'p_recovery_ur', 'rep_rate_r', 'rep_rate_ur', 'inh_res', 'd_rate_ui', 'd_rate', 'g_rate', 'c_cap',
           'sim_data', 'mortality', 'mortalitysim', 'years_list', 'months_list']
start = [1995, 7, 1]
end = [1999, 7, 1]
# confirmed_cases = [52.0, 78.0, 403.0, 104.0, 13.0, 91.0]
confirmed_cases = [52.0, 78.0, 403.0, 104.0, 13.0, 91.0, 36.0, 30.0, 0.0, 0.0, 0.0, 0.0, 6.0, 30.0, 132.0, 234.0, 66.0,
                   48.0, 15.0, 18.0, 6.0, 3.0, 0.0, 0.0, 30.0, 114.0, 177.0, 222.0, 39.0, 18.0, 3.0, 3.0, 0.0, 0.0, 0.0,
                   0.0, 12.0, 51.0, 54.0, 87.0, 27.0, 24.0, 24.0, 24.0, 8.0, 0.0, 8.0, 0.0]
# 1995 0, 0, 1, 0, 2, 0, 8, 12, 62, 16, 2, 14
# 1996 6, 5, 0, 0, 0, 0, 1, 5, 22, 39, 11, 8
# 1997 5, 6, 2, 1, 0, 0, 10, 38, 59, 74, 13, 6
# 1998 1, 1, 0, 0, 0, 0, 4, 17, 18, 29, 9, 8
# 1999 3, 3, 1, 0, 1, 0
# confirmed_cases = [0, 0, 1, 0, 2, 0, 8, 12, 62, 16, 2, 14, 6, 5, 0, 0, 0, 0, 1, 5, 22, 39, 11, 8, 5, 6, 2, 1, 0, 0,
#                    10, 38, 59, 74, 13, 6, 1, 1, 0, 0, 0, 0, 4, 17, 18, 29, 9, 8, 3, 3, 1, 0, 1, 0]
years_list = pd.date_range(date(start[0], start[1], start[2]), date(end[0], end[1], end[2])).tolist()
months_list = pd.date_range(date(start[0], start[1], start[2]), date(end[0], end[1], end[2]), freq='M').tolist()
# -- Params
data, temp_list = TempReader().cooked()
t = len(data)
# - human
rat_pop = pm.Uniform('rat_pop', 10, 15000.0, value=1100.0)
beta_h = pm.Uniform('beta_h', 1e-9, 0.6, value=0.21)
# .2
gamma_h = 0.2
p_recovery_h = .4
# - rat
# .08
temp_scale = pm.Uniform('temp_scale', 0.75, 1.25, value=0.95)
# 0.08
beta_r = pm.Uniform('beta_r', 1e-9, .99, value=0.069)
# .2
gamma_r = 0.2
# .1
p_recovery_ur = .1
rep_rate_r = .4 * (1 - 0.234)
rep_rate_ur = .4
inh_res = pm.Uniform('inh_res', 0.2, 0.99, value=0.966)
d_rate_ui = 1. / 365.
# - flea
d_rate = 0.2
# 0.2
g_rate = .0084
c_cap = 6.
# shrews
shrew_pop = 12000.
i_rpd = 2.


# -- Simulate
@pm.deterministic
def plague_model(rat_pop=rat_pop, beta_h=beta_h, temp_scale=temp_scale, beta_r=beta_r, inh_res=inh_res):
    # human
    n_h = 25000.
    i_h = np.zeros(t, dtype=float)
    i_n = np.zeros(len(confirmed_cases), dtype=float)
    r_h = np.zeros(t, dtype=float)
    d_h = np.zeros(t, dtype=float)
    d_h[0] = 1.
    i_h[0] = 0.
    # rat
    s_r = np.zeros(t, dtype=float)
    i_r = np.zeros(t, dtype=float)
    res_r = np.zeros(t, dtype=float)
    d_r = np.zeros(t, dtype=float)
    s_r[0] = rat_pop - 20.
    res_r[0] = 0.
    # flea
    searching = 3. / (rat_pop - 20)
    i_f = np.zeros(t, dtype=float)
    fph = np.zeros(t, dtype=float)
    fph[0] = 6.0
    m = 0
    month = 1
    for i, v in enumerate(years_list[1:], 1):
        # shrews
        if 189 <= v.timetuple().tm_yday <= 222:
            shrew_transference = i_rpd
        else:
            shrew_transference = 0
        date_string = v.strftime("%Y-%m-%d")
        temp = data[date_string][0] * temp_scale
        temp_fac = (temp - 15.) / 10.
        # + rec_r[i - 1]
        n_r = s_r[i - 1] + i_r[i - 1] + res_r[i - 1]
        # natural deaths
        natural_death_unresistant = (s_r[i - 1] * d_rate_ui)
        natural_death_resistant = (res_r[i - 1] * d_rate_ui)
        natural_death_infected = (i_r[i - 1] * d_rate_ui)
        # - Fleas
        if i == 1:
            infected_rat_deaths = d_h[0]
        if fph[i - 1] / c_cap < 1.:
            flea_growth = (g_rate * temp_fac) * (fph[i - 1] * (1. - (fph[i - 1] / c_cap)))
        elif fph[i - 1] / c_cap > 1.:
            flea_growth = -(g_rate * temp_fac) * (fph[i - 1] * (1. - (fph[i - 1] / c_cap)))
        else:
            flea_growth = 0.

        new_infectious = infected_rat_deaths * fph[i - 1]
        # could be made temperature dependent
        starvation_deaths = d_rate * i_f[i - 1]
        # number of fleas that find a human
        force_to_humans = min(i_f[i - 1], i_f[i - 1] * np.exp(float(-searching * n_r)))
        # number of fleas that find a rat
        force_to_rats = i_f[i - 1] - force_to_humans
        force_to_rats = force_to_rats * (0.75 - 0.25 * np.tanh(((temp * 9. / 5.) + 32.) - 80.))
        force_to_humans = force_to_humans * (0.75 - 0.25 * np.tanh(((temp * 9. / 5.) + 32.) - 80.))
        fph[i] = fph[i - 1] + flea_growth
        # should add dehydration
        i_f[i] = max(0.0, i_f[i - 1] + new_infectious - starvation_deaths)

        # - Rats
        new_infected_rats = beta_r * s_r[i - 1] * force_to_rats / n_r
        new_infected_rats = 0 if new_infected_rats < 0 else new_infected_rats
        new_removed_rats = gamma_r * (i_r[i - 1] - natural_death_infected)
        new_recovered_rats = p_recovery_ur * new_removed_rats
        new_dead_rats = new_removed_rats - new_recovered_rats
        infected_rat_deaths = new_dead_rats

        # born rats
        pressure = n_r / rat_pop
        resistant_born_rats = max(0, rep_rate_r * res_r[i - 1] * (inh_res - pressure))
        unresistant_born_rats = max(0, (rep_rate_r * res_r[i - 1] * (1 - inh_res)) + (rep_rate_ur * s_r[i - 1]
                                    * (1 - pressure)))

        # time step values
        s_r[i] = min(rat_pop, s_r[i - 1] + unresistant_born_rats - new_infected_rats - natural_death_unresistant
                     - shrew_transference)
        i_r[i] = i_r[i - 1] + new_infected_rats - new_removed_rats - natural_death_infected + shrew_transference
        res_r[i] = res_r[i - 1] + new_recovered_rats + resistant_born_rats - natural_death_resistant
        d_r[i] = new_dead_rats + natural_death_unresistant + natural_death_resistant + natural_death_infected

        # - Humans
        s_h = n_h - i_h[i - 1] - r_h[i - 1]
        new_infected_humans = min(n_h, beta_h * s_h * force_to_humans / n_h)
        new_removed_humans = gamma_h * i_h[i - 1]
        new_recovered_humans = p_recovery_h * new_removed_humans
        new_dead_humans = new_removed_humans - new_recovered_humans

        # time step values
        i_h[i] = i_h[i - 1] + new_infected_humans - new_removed_humans + 0.0000001
        r_h[i] = r_h[i - 1] + new_recovered_humans
        d_h[i] = new_dead_humans + 0.0000001
        this_month = int(date_string.split("-")[1])
        if month == this_month:
            i_n[m - 1] += new_infected_humans
        else:
            month = this_month
            m += 1
            if m <= len(i_n):
                i_n[m - 1] += new_infected_humans
            else:
                pass
    return i_n, i_h, r_h, d_h, s_r, i_r, res_r, d_r, i_f, fph


# Likelihood
sim_data = pm.Lambda('sim_data', lambda plague_model=plague_model: plague_model[0])
mortality = pm.Poisson('mortality', mu=sim_data, value=confirmed_cases, observed=True)
mortalitysim = pm.Poisson('mortality_sim', mu=sim_data)
