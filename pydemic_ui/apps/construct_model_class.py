class ConstructModel:
    def __init__(self, *, daily_cases, runner, period, disease, **kwargs):
        self.model = SEAIR(disease=disease, **kwargs)

        seair = calc_seair(
            daily_cases,
            self.model.incubation_period,
            self.model.infectious_period,
            self.model.Qs,
            self.model.population,
        )

        self.model.set_ic(state=seair.result)
        self.model = runner(self.model, period)

    def new_model(self):
        return self.model

    class calc_seair:
        def __init__(
            self, daily_cases, incubation_period, infectious_period, Qs, population
        ):
            self.daily_cases = daily_cases
            self.infectious_period = infectious_period
            self.incubation_period = incubation_period
            self.Qs = Qs
            self.population = population

            self.recovered = self.number_of_recovered()
            self.exposed = self.number_of_exposed()
            self.infectious = self.number_of_infectious()
            self.asymptomatic = self.number_of_asymptomatic(1 - Qs)
            self.susceptible = self.number_of_susceptible()

            self.result = (
                self.susceptible,
                self.exposed,
                self.asymptomatic,
                self.infectious,
                self.recovered,
            )

        def number_of_susceptible(self):
            return (
                self.population
                - self.exposed
                - self.asymptomatic
                - self.infectious
                - self.recovered
            )

        def number_of_exposed(self):
            return self.daily_cases * self.incubation_period

        def number_of_asymptomatic(self, reverse_qs):
            return self.daily_cases * self.infectious_period * reverse_qs

        def number_of_infectious(self):
            return self.daily_cases * self.infectious_period * self.Qs

        def number_of_recovered(self):
            return 0.0
