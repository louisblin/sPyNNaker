from spinn_utilities.overrides import overrides
from spynnaker.pyNN.models.abstract_models import AbstractContainsUnits
from .abstract_input_type import AbstractInputType


class InputTypeCurrent(AbstractInputType, AbstractContainsUnits):
    """ The current input type
    """

    def __init__(self):
        AbstractInputType.__init__(self)
        AbstractContainsUnits.__init__(self)
        self._units = {}

    def get_global_weight_scale(self):
        return 1.0

    def get_n_input_type_parameters(self):
        return 0

    def get_input_type_parameters(self):
        return []

    def get_input_type_parameter_types(self):
        return []

    def get_n_cpu_cycles_per_neuron(self, n_synapse_types):
        return 0

    @overrides(AbstractContainsUnits.get_units)
    def get_units(self, variable):
        return self._units[variable]
