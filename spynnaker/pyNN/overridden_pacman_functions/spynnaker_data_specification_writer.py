from spinn_front_end_common.interface.interface_functions import \
    GraphDataSpecificationWriter

from spynnaker.pyNN.models.utility_models import DelayExtensionVertex


class SpynnakerDataSpecificationWriter(GraphDataSpecificationWriter):
    """ Executes data specification generation for sPyNNaker. The main \
        difference from the standard one is that this puts delay extensions \
        after all other vertices.
    """

    __slots__ = ()

    def __call__(
            self, placements, graph, hostname,
            report_default_directory, write_text_specs,
            app_data_runtime_folder, machine, graph_mapper=None):
        # pylint: disable=too-many-arguments
        return super(SpynnakerDataSpecificationWriter, self).__call__(
            placements, hostname, report_default_directory, write_text_specs,
            app_data_runtime_folder, machine, graph_mapper,
            placement_order=self._sort_delays_to_end(
                placements.placements, graph_mapper))

    @staticmethod
    def _sort_delays_to_end(plist, graph_mapper):
        placements = list()
        delay_extension_placements = list()
        for placement in plist:
            vertex = graph_mapper.get_application_vertex(placement.vertex)
            if isinstance(vertex, DelayExtensionVertex):
                delay_extension_placements.append((placement, vertex))
            else:
                placements.append((placement, vertex))
        placements.extend(delay_extension_placements)
        return placements
