#include <pybind11/pybind11.h>

#include <iostream>
#include <tuple>

#include <routingblocks/arc.h>
#include <routingblocks/evaluation.h>
#include <routingblocks/Solution.h>
#include <routingblocks/node.h>
#include <routingblocks/vertex.h>
#include <routingblocks/binding_helpers.hpp>

#define STRINGIFY(x) #x
#define PREPROCESSOR_TO_STRING(x) STRINGIFY(x)

#ifndef ROUTINGBLOCKS_EXT_MODULE_VERSION
#    define ROUTINGBLOCKS_EXT_MODULE_VERSION "dev"
#endif

using label_holder_t = routingblocks::detail::label_holder;

struct HFVRP_forward_label {
    resource_t distance;
    resource_t load_weight;
    resource_t load_volume;

    HFVRP_forward_label(resource_t distance, resource_t load_weight, resource_t load_volume) : distance(distance), load_weight(load_weight), load_volume(load_volume) {}
};

struct HFVRP_backward_label {
    resource_t distance;
    resource_t load_weight;
    resource_t load_volume;

    HFVRP_backward_label(resource_t distance, resource_t load_weight, resource_t load_volume) : distance(distance), load_weight(load_weight), load_volume(load_volume) {}
};
struct HFVRP_vertex_data {
    resource_t demand_weight;
    resource_t demand_volume;

    HFVRP_vertex_data(resource_t demand_weight, resource_t demand_volume) : demand_weight(demand_weight), demand_volume(demand_volume) {}
};
struct HFVRP_arc_data {
    resource_t distance;

    HFVRP_arc_data(resource_t distance) : distance(distance) {}
};

class HFVRPEvaluation
    : public routingblocks::ConcatenationBasedEvaluationImpl<HFVRPEvaluation, HFVRP_forward_label,
                                                     HFVRP_backward_label, HFVRP_vertex_data,
                                                     HFVRP_arc_data> {
  public:
    enum CostComponent {
        DIST_INDEX = 0,
        RANGE_INDEX = 1,
        OVERLOAD_WEIGHT_INDEX = 2,
        OVERLOAD_VOLUME_INDEX = 3,
    };

  private:
    int num_vehicles;
    std::vector<resource_t> _acquisition_cost;
    std::vector<resource_t> _storage_weight_capacity;
    std::vector<resource_t> _storage_volume_capacity;
    std::vector<resource_t> _max_range;

    double _overload_penalty_factor = 1.; // <- one penalty factor for both - change if needed ;)
    double _range_excess_penalty_factor = 1.;

  public:
    HFVRPEvaluation(pybind11::list vehicle_properties) {
         num_vehicles = pybind11::len(vehicle_properties);
         _acquisition_cost = std::vector<resource_t>();
         _acquisition_cost.reserve(num_vehicles);
         _storage_weight_capacity = std::vector<resource_t>();
         _storage_weight_capacity.reserve(num_vehicles);
         _storage_volume_capacity = std::vector<resource_t>();
         _storage_volume_capacity.reserve(num_vehicles);
         _max_range = std::vector<resource_t>();
         _max_range.reserve(num_vehicles);


         for (auto item : vehicle_properties) {
            auto props = item.cast<pybind11::tuple>();
            _acquisition_cost.push_back(props[0].cast<resource_t>());
            _storage_weight_capacity.push_back(props[1].cast<resource_t>());
            _storage_volume_capacity.push_back(props[2].cast<resource_t>());
            _max_range.push_back(props[3].cast<resource_t>());
        }
    };

  private:
    cost_t _compute_cost_for_vehicle_id(size_t vehicle_id, resource_t distance, resource_t load_weight, resource_t load_volume) const {
        auto overload_weight = std::max(resource_t(0), load_weight - _storage_weight_capacity[vehicle_id]);
        auto overload_volume = std::max(resource_t(0), load_volume - _storage_volume_capacity[vehicle_id]);
        auto range_excess = std::max(resource_t(0), distance - _max_range[vehicle_id]);
        return static_cast<cost_t>(distance)
               + static_cast<cost_t>(_acquisition_cost[vehicle_id])
               + static_cast<cost_t>(overload_weight * _overload_penalty_factor)
               + static_cast<cost_t>(overload_volume * _overload_penalty_factor)
               + static_cast<cost_t>(range_excess  * _range_excess_penalty_factor);
    }

    std::pair<size_t, cost_t> _compute_best_vehicle_and_cost(resource_t distance, resource_t load_weight, resource_t load_volume) const {
        auto min_vehicle_idx = 0;
        auto min_vehicle_cost = _compute_cost_for_vehicle_id(0, distance, load_weight, load_volume);
        for (auto i = 1; i < num_vehicles; i++) {
            auto cost = _compute_cost_for_vehicle_id(i, distance, load_weight, load_volume);
            if (cost < min_vehicle_cost) {
                min_vehicle_idx = i;
                min_vehicle_cost = cost;
            }
        }
        return std::make_pair(min_vehicle_idx, min_vehicle_cost);
    }

  public:
    double get_overload_penalty_factor() const { return _overload_penalty_factor; }
    void set_overload_penalty_factor(double overload_penalty_factor) {
        _overload_penalty_factor = overload_penalty_factor;
    }

    double get_range_excess_penalty_factor() const { return _range_excess_penalty_factor; }
    void set_range_excess_penalty_factor(double range_excess_penalty_factor) {
        _range_excess_penalty_factor = range_excess_penalty_factor;
    }

    cost_t concatenate(const HFVRP_forward_label& fwd, const HFVRP_backward_label& bwd,
                       const routingblocks::Vertex& vertex, const HFVRP_vertex_data& vertex_data) {
        return _compute_best_vehicle_and_cost(fwd.distance + bwd.distance, fwd.load_weight + bwd.load_weight, fwd.load_volume + bwd.load_volume).second;
    }

    [[nodiscard]] std::vector<resource_t> get_cost_components(const HFVRP_forward_label& fwd) const {
        auto min_vehicle_idx = _compute_best_vehicle_and_cost(fwd.distance, fwd.load_weight, fwd.load_volume).first;
        return {fwd.distance, std::max(resource_t(0), fwd.distance - _max_range[min_vehicle_idx]),
                std::max(resource_t(0), fwd.load_weight - _storage_weight_capacity[min_vehicle_idx]),
                std::max(resource_t(0), fwd.load_volume - _storage_volume_capacity[min_vehicle_idx])};
    };

    [[nodiscard]] cost_t compute_cost(const HFVRP_forward_label& label) const {
        return _compute_best_vehicle_and_cost(label.distance, label.load_weight, label.load_volume).second;
    };

    [[nodiscard]] size_t compute_best_vehicle_id_of_route(const routingblocks::Route& route) const {
        const HFVRP_forward_label& label = route.end_depot()->forward_label().get<HFVRP_forward_label>();
        return _compute_best_vehicle_and_cost(label.distance, label.load_weight, label.load_volume).first;
    };

    [[nodiscard]] bool is_feasible(const HFVRP_forward_label& fwd) const {
        auto min_vehicle_idx = _compute_best_vehicle_and_cost(fwd.distance, fwd.load_weight, fwd.load_volume).first;
        return fwd.load_weight <= _storage_weight_capacity[min_vehicle_idx]
                    && fwd.load_volume <= _storage_volume_capacity[min_vehicle_idx]
                    && fwd.distance <= _max_range[min_vehicle_idx];
    };

    [[nodiscard]] HFVRP_forward_label propagate_forward(const HFVRP_forward_label& pred_label,
                                                       const routingblocks::Vertex& pred_vertex,
                                                       const HFVRP_vertex_data& pred_vertex_data,
                                                       const routingblocks::Vertex& vertex,
                                                       const HFVRP_vertex_data& vertex_data,
                                                       const routingblocks::Arc& arc,
                                                       const HFVRP_arc_data& arc_data) const {
        return {pred_label.distance + arc_data.distance, pred_label.load_weight + vertex_data.demand_weight, pred_label.load_volume + vertex_data.demand_volume};
    };

    [[nodiscard]] HFVRP_backward_label propagate_backward(const HFVRP_backward_label& succ_label,
                                                         const routingblocks::Vertex& succ_vertex,
                                                         const HFVRP_vertex_data& succ_vertex_data,
                                                         const routingblocks::Vertex& vertex,
                                                         const HFVRP_vertex_data& vertex_data,
                                                         const routingblocks::Arc& arc,
                                                         const HFVRP_arc_data& arc_data) const {
        return {succ_label.distance + arc_data.distance, succ_label.load_weight + succ_vertex_data.demand_weight, succ_label.load_volume + succ_vertex_data.demand_volume};
    };

    HFVRP_forward_label create_forward_label(const routingblocks::Vertex& vertex,
                                            const HFVRP_vertex_data& vertex_data) {
        return {0, vertex_data.demand_weight, vertex_data.demand_volume};
    };

    HFVRP_backward_label create_backward_label(const routingblocks::Vertex& vertex,
                                              const HFVRP_vertex_data& vertex_data) {
        return {0, 0, 0};
    };
};

PYBIND11_MODULE(ROUTINGBLOCKS_EXT_MODULE_NAME, m) {
    m.attr("__version__") = PREPROCESSOR_TO_STRING(ROUTINGBLOCKS_EXT_MODULE_VERSION);

    auto hfvrp_evaluation = pybind11::class_<HFVRPEvaluation, routingblocks::Evaluation>(m, "HFVRPEvaluation")
        .def(pybind11::init<pybind11::list>())
        .def("concatenate", &HFVRPEvaluation::concatenate)
        .def("compute_cost", &HFVRPEvaluation::compute_cost)
        .def("compute_best_vehicle_id_of_route", &HFVRPEvaluation::compute_best_vehicle_id_of_route)
        .def("is_feasible", &HFVRPEvaluation::is_feasible)
        .def("get_cost_components", &HFVRPEvaluation::get_cost_components)
        .def("propagate_forward", &HFVRPEvaluation::propagate_forward)
        .def("propagate_backward", &HFVRPEvaluation::propagate_backward)
        .def("create_forward_label", &HFVRPEvaluation::create_forward_label)
        .def("create_backward_label", &HFVRPEvaluation::create_backward_label);

    hfvrp_evaluation.def_property("overload_penalty_factor",
                                 &HFVRPEvaluation::get_overload_penalty_factor,
                                 &HFVRPEvaluation::set_overload_penalty_factor);

    hfvrp_evaluation.def_property("range_excess_penalty_factor",
                                 &HFVRPEvaluation::get_range_excess_penalty_factor,
                                 &HFVRPEvaluation::set_range_excess_penalty_factor);

    pybind11::class_<HFVRP_forward_label>(m, "HFVRPForwardLabel")
        .def_property_readonly("distance",
                               [](const HFVRP_forward_label& label) { return label.distance; })
        .def_property_readonly("load_weight", [](const HFVRP_forward_label& label) { return label.load_weight; })
        .def_property_readonly("load_volume", [](const HFVRP_forward_label& label) { return label.load_volume; });

    pybind11::class_<HFVRP_backward_label>(m, "HFVRPBackwardLabel")
        .def_property_readonly("distance",
                               [](const HFVRP_backward_label& label) { return label.distance; })
        .def_property_readonly("load_weight", [](const HFVRP_backward_label& label) { return label.load_weight; })
        .def_property_readonly("load_volume", [](const HFVRP_backward_label& label) { return label.load_volume; });

    pybind11::class_<HFVRP_vertex_data>(m, "HFVRPVertexData")
        .def(pybind11::init<resource_t, resource_t>())
        .def_property_readonly("demand_weight", [](const HFVRP_vertex_data& data) { return data.demand_weight; })
        .def_property_readonly("demand_volume", [](const HFVRP_vertex_data& data) { return data.demand_volume; });

    pybind11::class_<HFVRP_arc_data>(m, "HFVRPArcData")
        .def(pybind11::init<resource_t>())
        .def_property_readonly("distance", [](const HFVRP_arc_data& data) { return data.distance; });

    m.def("create_hfvrp_vertex", &::bindings::helpers::vertex_constructor<HFVRP_vertex_data>);
    m.def("create_hfvrp_arc", &::bindings::helpers::arc_constructor<HFVRP_arc_data>);
}