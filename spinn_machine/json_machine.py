import logging

from .chip import Chip
from .machine import Machine
from .processor import Processor
from .router import Router
from .sdram import SDRAM
from .link import Link
from collections import defaultdict, namedtuple, OrderedDict
import json


logger = logging.getLogger(__name__)

# A description of a standard set of resources possessed by a chip
_Desc = namedtuple("_Desc", [
    # The cores where the monitors are
    "monitors",
    # The entries on the router
    "router_entries",
    # The speed of the router
    "router_clock_speed",
    # The amount of SDRAM on the chip
    "sdram",
    # Whether this is a virtual chip
    "virtual",
    # What tags this chip has
    "tags"])

JAVA_MAX_INT = 2147483647
OPPOSITE_LINK_OFFSET = 3


class JsonMachine(Machine):
    """ A Virtual SpiNNaker machine based on json
    """

    __slots__ = ()

    # pylint: disable=too-maa  ny-arguments
    def __init__(self, j_machine):
        """
        :param j_machine: json description of the machine
        :type j_machine: dict in format returned by json.load or a
            str representing a path to the json file
        """
        super(JsonMachine, self).__init__((), 0, 0)

        #
        if isinstance(j_machine, str):
            with open(j_machine) as j_file:
                j_machine = json.load(j_file)

        processors_by_cores = {}

        # get the default values
        width = j_machine["width"]
        height = j_machine["height"]
        s_monitors = j_machine["standardResources"]["monitors"]
        s_router_entries = j_machine["standardResources"]["routerEntries"]
        s_router_clock_speed = \
            j_machine["standardResources"]["routerClockSpeed"]
        s_sdram = SDRAM(j_machine["standardResources"]["sdram"])
        s_tag_ids = j_machine["standardResources"]["tags"]

        e_monitors = j_machine["ethernetResources"]["monitors"]
        e_router_entries = j_machine["ethernetResources"]["routerEntries"]
        e_router_clock_speed = \
            j_machine["ethernetResources"]["routerClockSpeed"]
        e_sdram = SDRAM(j_machine["ethernetResources"]["sdram"])
        e_tag_ids = j_machine["ethernetResources"]["tags"]

        for j_chip in j_machine["chips"]:
            details = j_chip[2]
            source_x = j_chip[0]
            source_y = j_chip[1]
            nearest_ethernet = details["ethernet"]

            # get the details
            if "ipAddress" in details:
                ip_address = details["ipAddress"]
                clock_speed = e_router_clock_speed
                router_entries = e_router_entries
                sdram = e_sdram
                tag_ids = e_tag_ids
                monitors = e_monitors
            else:
                ip_address = None
                clock_speed = s_router_clock_speed
                router_entries = s_router_entries
                sdram = s_sdram
                tag_ids = s_tag_ids
                monitors = s_monitors
            if len(j_chip) > 3:
                exceptions = j_chip[3]
                if "monitors" in exceptions:
                    monitors = exceptions["monitors"]
                if "routerClockSpeed" in exceptions:
                    clock_speed = exceptions["routerClockSpeed"]
                if "routerEntries" in exceptions:
                    router_entries = exceptions["routerEntries"]
                if "sdram" in exceptions:
                    sdram = SDRAM(exceptions["sdram"])
                if "tags" in exceptions:
                    tag_ids = exceptions["tags"]

            # create a router based on the details
            processors = self._get_processors(
                details["cores"], monitors, processors_by_cores)
            if "deadLinks" in details:
                dead_links = details["deadLinks"]
            else:
                dead_links = []
            links = []
            for source_link_id in range(6):
                if source_link_id not in dead_links:
                    destination_x, destination_y = Machine.get_chip_over_link(
                        source_x, source_y, source_link_id, width, height)
                    opposite_link_id = (
                        (source_link_id + OPPOSITE_LINK_OFFSET) %
                        Router.MAX_LINKS_PER_ROUTER)
                    links.append(Link(
                        source_x, source_y, source_link_id, destination_x,
                        destination_y, opposite_link_id, opposite_link_id))
            router = Router(links, False, clock_speed, router_entries)

            # Create and add a chip with this router
            chip = Chip(
                source_x, source_y, processors, router, sdram,
                nearest_ethernet[0], nearest_ethernet[1], ip_address, False,
                tag_ids)
            self.add_chip(chip)

        self.add_spinnaker_links(version_no=None)
        self.add_fpga_links(version_no=None)

    @staticmethod
    def _get_processors(cores, monitors, processors_by_cores):
        if not (cores, monitors) in processors_by_cores:
            processors = []
            for i in range(0, monitors):
                processors.append(Processor.factory(0, True))
            for i in range(monitors, cores):
                processors.append(Processor.factory(i))
            processors_by_cores[(cores, monitors)] = processors
        return processors_by_cores[(cores, monitors)]

    def __str__(self):
        return "[JsonMachine: max_x={}, max_y={}, n_chips={}]".format(
            self._max_chip_x, self._max_chip_y, self.n_chips)

    @staticmethod
    def _int_value(value):
        if value < JAVA_MAX_INT:
            return value
        else:
            return JAVA_MAX_INT

    @staticmethod
    def _find_virtual_links(machine):
        """ Find all the virtual links and their inverse.

        As these may well go to an unexpected source

        :param machine: Machine to convert
        :return: Map of Chip to list of virtual links
        """
        virtual_links_dict = defaultdict(list)
        for chip in machine._virtual_chips:
            # assume all links need special treatment
            for link in chip.router.links:
                virtual_links_dict[chip].append(link)
                # Find and save inverse link as well
                inverse_id = ((link.source_link_id + OPPOSITE_LINK_OFFSET) %
                              Router.MAX_LINKS_PER_ROUTER)
                destination = machine.get_chip_at(
                    link.destination_x, link.destination_y)
                inverse_link = destination.router.get_link(inverse_id)
                assert(inverse_link.destination_x == chip.x)
                assert(inverse_link.destination_y == chip.y)
                virtual_links_dict[destination].append(inverse_link)
        return virtual_links_dict

    @staticmethod
    def _describe_chip(chip, std, eth, virtual_links_dict):
        """ Produce a JSON-suitable description of a single chip.

        :param chip: The chip to describe.
        :param std: The standard chip resources.
        :param eth: The standard ethernet chip resources.
        :param virtual_links_dict: Where the virtual links are.
        :return: Description of chip that is trivial to serialize as JSON.
        """
        details = OrderedDict()
        details["cores"] = chip.n_processors
        if chip.nearest_ethernet_x is not None:
            details["ethernet"] =\
                [chip.nearest_ethernet_x, chip.nearest_ethernet_y]

        dead_links = []
        for link_id in range(0, Router.MAX_LINKS_PER_ROUTER):
            if not chip.router.is_link(link_id):
                dead_links.append(link_id)
        if dead_links:
            details["deadLinks"] = dead_links

        if chip in virtual_links_dict:
            links = []
            for link in virtual_links_dict[chip]:
                link_details = OrderedDict()
                link_details["sourceLinkId"] = link.source_link_id
                link_details["destinationX"] = link.destination_x
                link_details["destinationY"] = link.destination_y
                links.append(link_details)
            details["links"] = links

        exceptions = OrderedDict()
        router_entries = JsonMachine._int_value(
            chip.router.n_available_multicast_entries)
        if chip.ip_address is not None:
            details['ipAddress'] = chip.ip_address
            # Write the Resources ONLY if different from the e_values
            if (chip.n_processors - chip.n_user_processors) != eth.monitors:
                exceptions["monitors"] = \
                    chip.n_processors - chip.n_user_processors
            if router_entries != eth.router_entries:
                exceptions["routerEntries"] = router_entries
            if chip.router.clock_speed != eth.router_clock_speed:
                exceptions["routerClockSpeed"] = \
                    chip.router.n_available_multicast_entries
            if chip.sdram.size != eth.sdram:
                exceptions["sdram"] = chip.sdram.size
            if chip.virtual != eth.virtual:
                exceptions["virtual"] = chip.virtual
            if chip.tag_ids != eth.tags:
                details["tags"] = list(chip.tag_ids)
        else:
            # Write the Resources ONLY if different from the s_values
            if (chip.n_processors - chip.n_user_processors) != std.monitors:
                exceptions["monitors"] = \
                    chip.n_processors - chip.n_user_processors
            if router_entries != std.router_entries:
                exceptions["routerEntries"] = router_entries
            if chip.router.clock_speed != std.router_clock_speed:
                exceptions["routerClockSpeed"] = \
                    chip.router.clock_speed
            if chip.sdram.size != std.sdram:
                exceptions["sdram"] = chip.sdram.size
            if chip.virtual != std.virtual:
                exceptions["virtual"] = chip.virtual
            if chip.tag_ids != std.tags:
                details["tags"] = list(chip.tag_ids)

        if exceptions:
            return [chip.x, chip.y, details, exceptions]
        else:
            return [chip.x, chip.y, details]

    @staticmethod
    def to_json(machine):
        """ Runs the code to write the machine in Java readable JSON.

        :param machine: Machine to convert
        :type machine: :py:class:`spinn_machine.machine.Machine`
        """

        # Find the std values for one non-ethernet chip to use as standard
        std = None
        for chip in machine.chips:
            if chip.ip_address is None:
                std = _Desc(
                    monitors=chip.n_processors - chip.n_user_processors,
                    router_entries=JsonMachine._int_value(
                        chip.router.n_available_multicast_entries),
                    router_clock_speed=chip.router.clock_speed,
                    sdram=chip.sdram.size,
                    virtual=chip.virtual,
                    tags=chip.tag_ids)
                break
        else:
            # Probably ought to warn if std is unpopulated
            pass

        # find the eth values to use for ethernet chips
        chip = machine.boot_chip
        eth = _Desc(
            monitors=chip.n_processors - chip.n_user_processors,
            router_entries=JsonMachine._int_value(
                chip.router.n_available_multicast_entries),
            router_clock_speed=chip.router.clock_speed,
            sdram=chip.sdram.size,
            virtual=chip.virtual,
            tags=chip.tag_ids)

        # Save the standard data to be used as defaults to none ethernet chips
        standard_resources = OrderedDict()
        standard_resources["monitors"] = std.monitors
        standard_resources["routerEntries"] = std.router_entries
        standard_resources["routerClockSpeed"] = std.router_clock_speed
        standard_resources["sdram"] = std.sdram
        standard_resources["virtual"] = std.virtual
        standard_resources["tags"] = list(std.tags)

        # Save the standard data to be used as defaults to none ethernet chips
        ethernet_resources = OrderedDict()
        ethernet_resources["monitors"] = eth.monitors
        ethernet_resources["routerEntries"] = eth.router_entries
        ethernet_resources["routerClockSpeed"] = eth.router_clock_speed
        ethernet_resources["sdram"] = eth.sdram
        ethernet_resources["virtual"] = eth.virtual
        ethernet_resources["tags"] = list(eth.tags)

        # write basic stuff
        json_obj = OrderedDict()
        json_obj["height"] = machine.max_chip_y + 1
        json_obj["width"] = machine.max_chip_x + 1
        json_obj["root"] = list((machine.boot_x, machine.boot_y))
        json_obj["standardResources"] = standard_resources
        json_obj["ethernetResources"] = ethernet_resources
        json_obj["chips"] = []

        virtual_links_dict = JsonMachine._find_virtual_links(machine)

        # handle chips
        for chip in machine.chips:
            json_obj["chips"].append(JsonMachine._describe_chip(
                chip, std, eth, virtual_links_dict))

        return json_obj

    @staticmethod
    def to_json_path(machine, file_path):
        """ Runs the code to write the machine in Java readable JSON.

        :param machine: Machine to convert
        :type machine: :py:class:`spinn_machine.machine.Machine`
        :param file_path: Location to write file to. Warning will overwrite!
        :type file_path: str
        """
        json_obj = JsonMachine.to_json(machine)

        # dump to json file
        with open(file_path, "w") as f:
            json.dump(json_obj, f)