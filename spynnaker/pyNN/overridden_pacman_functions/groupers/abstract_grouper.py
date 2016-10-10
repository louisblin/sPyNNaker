from pacman.model.constraints.partitioner_constraints.\
    partitioner_same_size_as_vertex_constraint \
    import PartitionerSameSizeAsVertexConstraint

from spinn_front_end_common.utilities import exceptions
from spinn_machine.utilities.progress_bar import ProgressBar

from spynnaker.pyNN import DelayExtensionVertex
from spynnaker.pyNN.models.neural_projections.projection_application_edge \
    import ProjectionApplicationEdge
from spynnaker.pyNN.models.neural_projections.delay_afferent_application_edge \
    import DelayAfferentApplicationEdge
from spynnaker.pyNN.models.neural_projections.delayed_application_edge \
    import DelayedApplicationEdge
from spynnaker.pyNN.models.neural_projections.synapse_information \
    import SynapseInformation
from spynnaker.pyNN.models.neuron.connection_holder import ConnectionHolder
from spynnaker.pyNN.utilities import constants

import logging
import math
logger = logging.getLogger(__name__)


class AbstractGrouper(object):
    """ Provides basic functionality for grouping algorithms
    """

    def handle_projections(
            self, projections, population_to_vertices,
            user_max_delay, graph, using_virtual_board):
        """ Handle the addition of projections

        :param projections: the list of projections from the pynn level
        :param population_atom_mapping: the mapping from pops and model types
        :param pop_to_vertex_mapping: the mapping of pop views and atoms
        :param user_max_delay: the end users max delay
        :param partitionable_graph: the partitionable graph to add edges into
        :param using_virtual_board: if the end user is using a virtual board.
        :return: None
        """

        # hold a vertex to delay vertex map for tracking which vertices
        # have delays already
        vertex_to_delay_vertex = dict()

        progress_bar = ProgressBar(
            len(projections), "Creating Edges")

        # iterate through projections and create edges
        for projection in projections:

            # Get the presynaptic and postsynaptic vertices
            pre_vertices = population_to_vertices[
                projection._presynaptic_population]
            post_vertices = population_to_vertices[
                projection._postsynaptic_population]

            # For each pair of vertices, add edges
            for pre_vertex in pre_vertices:
                for post_vertex in post_vertices:

                    # get the synapse type
                    synapse_type = self._get_synapse_type(
                        post_vertex, projection._postsynaptic_population,
                        projection.target)

                    # Set and store information for future processing
                    synapse_information = SynapseInformation(
                        projection._connector,
                        projection._post_synaptic_population._synapse_dynamics,
                        synapse_type)

                    # get synapse information
                    synapse_information = self._get_synapse_info(
                        projection._connector, synapse_type, population_atom_mapping,
                        postsynaptic_population, presynaptic_population,
                        projection._rng)

            # get populations from the projection
            presynaptic_population = projection._presynaptic_population
            postsynaptic_population = projection._postsynaptic_population

            # get mapped vertex's and their sections for the pops.
            post_pop_vertex = pop_to_vertex_mapping[postsynaptic_population]
            pre_pop_vertex = pop_to_vertex_mapping[presynaptic_population]

            # inform the projection of its synapse into
            projection._synapse_information = synapse_information

            # add delay extensions and edges as required
            self._sort_out_delays(
                post_pop_vertex, pre_pop_vertex, postsynaptic_population,
                presynaptic_population, population_atom_mapping,
                synapse_information, projection, user_max_delay,
                partitionable_graph, using_virtual_board,
                delay_to_vertex_mapping)
            progress_bar.update()
        progress_bar.end()

    def _sort_out_delays(
            self, post_pop_vertex, pre_pop_vertex, postsynaptic_population,
            presynaptic_population, population_atom_mapping,
            synapse_information, projection, user_max_delay,
            partitionable_graph, using_virtual_board, delay_to_vertex_mapping):
        """
        goes through a edge looking at the delays required from it due to the
        synaptic dynamics and does some checks on the delay before moving
        on.
        :param post_pop_vertex: The destination vertex of this edge
        :param pre_pop_vertex: The source vertex of this edge
        :param postsynaptic_population: the destination population
        :param presynaptic_population: the source population
        :param population_atom_mapping: the atom mapping for the populations
        :param synapse_information: the synapse info generated by the projection
        :param projection: the projection this is all being considered for
        :param user_max_delay: the end user max delay
        :param partitionable_graph: the partitionable graph the edges are to
         be added to
        :param using_virtual_board: flag for stating if the machine is virtual
        :param delay_to_vertex_mapping: the mapping of vertices which have a
        delay extension added to them.
        :return: None
        """

        # check if all delays requested can fit into the natively supported
        # delays in the models
        synapse_dynamics_stdp = synapse_information.synapse_dynamics
        max_delay = \
            synapse_dynamics_stdp.get_delay_maximum(projection._connector)
        if max_delay is None:
            max_delay = user_max_delay
        delay_extension_max_supported_delay = (
            constants.MAX_DELAY_BLOCKS *
            constants.MAX_TIMER_TICS_SUPPORTED_PER_BLOCK)

        # get post vertex max delay
        post_vertex_max_supported_delay_ms = \
            post_pop_vertex.maximum_delay_supported_in_ms

        # verify that the max delay is less than the max supported by the
        # implementation of delays
        if max_delay > (post_vertex_max_supported_delay_ms +
                        delay_extension_max_supported_delay):
            raise exceptions.ConfigurationException(
                "The maximum delay {} for projection is not supported".format(
                    max_delay))

        # all atoms from a given pop have the same synapse dynamics,
        #  machine_time_step, and time_scale_factor so get from population
        pop_atoms = population_atom_mapping[
            postsynaptic_population._class][postsynaptic_population]
        machine_time_step = \
            pop_atoms[0].population_parameters["machine_time_step"]
        time_scale_factor = \
            pop_atoms[0].population_parameters["time_scale_factor"]

        # verify max delay is less than the max delay entered by the user
        # during setup.
        if max_delay > (user_max_delay / (machine_time_step / 1000.0)):
            logger.warn("The end user entered a max delay"
                        " for which the projection breaks")

        # handle edge processing
        self._handle_edge(
            post_pop_vertex, pre_pop_vertex, projection, synapse_information,
            partitionable_graph, max_delay, post_vertex_max_supported_delay_ms,
            presynaptic_population, postsynaptic_population,
            using_virtual_board, machine_time_step, time_scale_factor,
            delay_to_vertex_mapping)

    def _handle_edge(
            self, post_pop_vertex, pre_pop_vertex, projection,
            synapse_information, partitionable_graph, max_delay,
            post_vertex_max_supported_delay_ms, presynaptic_population,
            postsynaptic_population, using_virtual_board, machine_time_step,
            time_scale_factor, delay_to_vertex_mapping):
        """
        takes a edge and checks if a delay extension is needed or if there's
        already an edge to add this data to.
        :param post_pop_vertex: The destination vertex of this edge
        :param pre_pop_vertex: The source vertex of this edge
        :param postsynaptic_population: the destination population
        :param presynaptic_population: the source population
        :param synapse_information: the synapse info generated by the projection
        :param projection: the projection this is all being considered for
        :param max_delay: the end user max delay
        :param partitionable_graph: the partitionable graph the edges are to
         be added to
        :param using_virtual_board: flag for stating if the machine is virtual
        :param delay_to_vertex_mapping: the mapping of vertices which have a
        delay extension added to them.
        :return: None
        """

        # Find out if there is an existing edge between the populations
        edge_to_merge = self._find_existing_edge(
            pre_pop_vertex, post_pop_vertex, partitionable_graph)

        # if there's a edge, merge, else make edge
        if edge_to_merge is not None:

            # If there is an existing edge, add the connector
            edge_to_merge.add_synapse_information(synapse_information)
            projection_edge = edge_to_merge
        else:

            # If there isn't an existing edge, create a new one
            projection_edge = ProjectionApplicationEdge(
                pre_pop_vertex, post_pop_vertex, synapse_information,
                projection, label=projection.label)

            # add to graph
            partitionable_graph.add_edge(projection_edge,
                                         projection.EDGE_PARTITION_ID)

        # update projection
        projection._projection_edge = projection_edge

        # If the delay exceeds the post vertex delay, add a delay extension
        if max_delay > post_vertex_max_supported_delay_ms:
            delay_edge = self._add_delay_extension(
                pre_pop_vertex, post_pop_vertex,
                max_delay, post_vertex_max_supported_delay_ms,
                machine_time_step, time_scale_factor, partitionable_graph,
                projection, delay_to_vertex_mapping, synapse_information)
            projection_edge.delay_edge = delay_edge

        # If there is a virtual board, we need to hold the data in case the
        # user asks for it
        if using_virtual_board:
            virtual_connection_list = list()
            connection_holder = ConnectionHolder(
                None, False, presynaptic_population.size,
                postsynaptic_population.size,
                virtual_connection_list)

            post_pop_vertex.add_pre_run_connection_holder(
                connection_holder, projection_edge,
                synapse_information)

            projection._virtual_connection_list = virtual_connection_list

    def _add_delay_extension(
            self,
            pre_pop_vertex, post_pop_vertex, max_delay_for_projection,
            max_delay_per_neuron, machine_time_step, timescale_factor,
            partitionable_graph, projection, delay_to_vertex_mapping,
            synapse_information):
        """
        Instantiate delay extension component of this edge.
        :param pre_pop_vertex: The destination vertex of this edge
        :param post_pop_vertex:  The source vertex of this edge
        :param max_delay_for_projection: The max supported delay for this
        projection
        :param max_delay_per_neuron: the max delay supported by the destination
        neuron model impl.
        :param machine_time_step: The machine time step of the simulation
        :param timescale_factor: the time scale factor of the simulation
        :param partitionable_graph: the partitionable graph the edges are to
         be added to
        :param projection:the projection this is all being considered for
        :param delay_to_vertex_mapping:the mapping of vertices which have a
        delay extension added to them.
        :return: the delay edge
        """

        # Create a delay extension vertex to do the extra delays
        delay_vertex = None
        if pre_pop_vertex in delay_to_vertex_mapping:
            delay_vertex = delay_to_vertex_mapping[pre_pop_vertex]

        if delay_vertex is None:

            # build a delay vertex
            delay_name = "{}_delayed".format(pre_pop_vertex.label)
            delay_vertex = DelayExtensionVertex(
                pre_pop_vertex.n_atoms, max_delay_per_neuron, pre_pop_vertex,
                machine_time_step, timescale_factor, label=delay_name)

            # store in map for other projections
            delay_to_vertex_mapping[pre_pop_vertex] = delay_vertex

            # add partitioner constraint to the pre pop vertex
            pre_pop_vertex.add_constraint(
                PartitionerSameSizeAsVertexConstraint(delay_vertex))
            partitionable_graph.add_vertex(delay_vertex)

            # Add the edge
            delay_afferent_edge = DelayAfferentApplicationEdge(
                pre_pop_vertex, delay_vertex,
                label="{}_to_DelayExtension".format(pre_pop_vertex.label))
            partitionable_graph.add_edge(delay_afferent_edge,
                                         projection.EDGE_PARTITION_ID)

        # Ensure that the delay extension knows how many states it will support
        n_stages = int(math.ceil(
            float(max_delay_for_projection - max_delay_per_neuron) /
            float(max_delay_per_neuron)))
        if n_stages > delay_vertex.n_delay_stages:
            delay_vertex.n_delay_stages = n_stages

        # Create the delay edge if there isn't one already
        delay_edge = self._find_existing_edge(
            delay_vertex, post_pop_vertex, partitionable_graph)
        if delay_edge is None:
            delay_edge = DelayedApplicationEdge(
                delay_vertex, post_pop_vertex, synapse_information,
                label="{}_delayed_to_{}".format(
                    pre_pop_vertex.label, post_pop_vertex.label))
            partitionable_graph.add_edge(
                delay_edge, projection.EDGE_PARTITION_ID)
        return delay_edge

    @staticmethod
    def _get_synapse_info(
            projection_connector, synapse_type, synapse_dynamics,
            postsynaptic_population, presynaptic_population, projection_rng):
        """
        returns a synapse info object from the projection's connector and
        atom mapping
        :param projection_connector: the connector that resides within
        the projection
        :param synapse_type: the type of synapse currently being considered
        :param population_atom_mapping: the atom to oop mapping
        :param postsynaptic_population: the destination population
        :param presynaptic_population: the source population
        :param projection_rng: the random number generator for the projection
        :return: synapse information object
        """

        # all atoms from a given pop have the same synapse dynamics
        #  so get first atom's
        pop_atoms = population_atom_mapping[
            postsynaptic_population._class][postsynaptic_population]
        synapse_dynamics_stdp = pop_atoms[0].synapse_dynamics

        # all atoms from a given pop have the same machine time step so
        # get from the population.
        machine_time_step = \
            pop_atoms[0].population_parameters["machine_time_step"]

        # Set and store information for future processing
        synapse_information = SynapseInformation(
            projection_connector, synapse_dynamics_stdp, synapse_type)

        # update the connector with projection info.
        projection_connector.set_projection_information(
            presynaptic_population, postsynaptic_population, projection_rng,
            machine_time_step)
        return synapse_information

    @staticmethod
    def _get_synapse_type(
            post_population_vertex, postsynaptic_population, target):
        """
        locate the synapse type for a projection from the post vertex
        :param post_population_vertex: destination vertex which holds
        the destination population of a edge
        :param postsynaptic_population: the destination population from the edge
        :param target: the target of the synapse.
        :return:
        """
        synapse_type = post_population_vertex.synapse_type.\
            get_synapse_id_by_target(target)
        if synapse_type is None:
            raise exceptions.ConfigurationException(
                "Synapse target {} not found in {}".format(
                    target, postsynaptic_population.label))
        return synapse_type

    @staticmethod
    def _find_existing_edge(
            presynaptic_vertex, postsynaptic_vertex, partitionable_graph):
        """ Searches though the partitionable graph's edges to locate any\
            edge which has the same post and pre vertex

        :param presynaptic_vertex: the source partitionable vertex of the\
                multapse
        :type presynaptic_vertex: instance of\
                pacman.model.partitionable_graph.abstract_partitionable_vertex
        :param postsynaptic_vertex: The destination partitionable vertex of\
                the multapse
        :type postsynaptic_vertex: instance of\
                pacman.model.partitionable_graph.abstract_partitionable_vertex
        :return: None or the edge going to these vertices.
        """
        graph_edges = partitionable_graph.edges
        for edge in graph_edges:
            if ((edge.pre_vertex == presynaptic_vertex) and
                    (edge.post_vertex == postsynaptic_vertex)):
                return edge
        return None
