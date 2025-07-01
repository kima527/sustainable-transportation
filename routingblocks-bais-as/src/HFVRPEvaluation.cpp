#include <pybind11/pybind11.h>
namespace py = pybind11;                 // NEW  ← lets us write py::arg()

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

constexpr resource_t SERVICE_SEC = 15 * 60;          // 15 min unloading

struct CityParams {
    resource_t utility_other;
    resource_t maintenance_cost;
    resource_t price_elec;
    resource_t price_diesel;
    resource_t hours_per_day;
    resource_t wage_semi;
    resource_t wage_heavy;
};

struct HFVRP_forward_label {
    resource_t distance;
    resource_t load_weight;
    resource_t load_volume;
    resource_t work_time;

    HFVRP_forward_label(resource_t d, resource_t w, resource_t v,
                        resource_t t)
        : distance(d), load_weight(w), load_volume(v), work_time(t) {}
};

struct HFVRP_backward_label {
    resource_t distance;
    resource_t load_weight;
    resource_t load_volume;
    resource_t work_time;

    HFVRP_backward_label(resource_t d, resource_t w, resource_t v,
                         resource_t t)                 // FIX  — add ‘t’
        : distance(d), load_weight(w), load_volume(v), work_time(t) {}
};

struct HFVRP_vertex_data {
    resource_t demand_weight;
    resource_t demand_volume;
    HFVRP_vertex_data(resource_t w, resource_t v)
        : demand_weight(w), demand_volume(v) {}
};

struct HFVRP_arc_data {
    resource_t distance;
    resource_t travel_time;
    HFVRP_arc_data(resource_t d, resource_t t) : distance(d), travel_time(t) {}
};

class HFVRPEvaluation
        : public routingblocks::ConcatenationBasedEvaluationImpl<
              HFVRPEvaluation, HFVRP_forward_label, HFVRP_backward_label,
              HFVRP_vertex_data, HFVRP_arc_data> {
  public:
    enum CostComponent { DIST = 0, RANGE = 1, OVER_W = 2,
                         OVER_V = 3, OVERTIME = 4 };
    std::vector<resource_t> acq, cap_w, cap_v, rng;


  private:
    int num_veh;
    // std::vector<resource_t> acq, cap_w, cap_v, rng;
    resource_t max_work_time;
    double pen_over   = 1.0, pen_range = 1.0, pen_time = 1.0;
    resource_t utility_other     = 0.0;
    resource_t maintenance_cost  = 0.0;
    resource_t price_elec        = 0.0;
    resource_t price_diesel      = 0.0;
    resource_t hours_per_day     = 8.0;
    resource_t wage_semi         = 0.0;
    resource_t wage_heavy        = 0.0;


  public:
    double get_overload_penalty_factor()      const { return _overload_penalty_factor; }
    void   set_overload_penalty_factor(double f)    { _overload_penalty_factor = f; }

    double get_range_excess_penalty_factor()  const { return _range_excess_penalty_factor; }
    void   set_range_excess_penalty_factor(double f){ _range_excess_penalty_factor = f; }

    double get_worktime_penalty_factor()      const { return _worktime_penalty_factor; }
    void   set_worktime_penalty_factor(double f)    { _worktime_penalty_factor = f; }

    double get_utility_other()      const { return utility_other; }
    double get_maintenance_cost()   const { return maintenance_cost; }
    double get_price_elec()         const { return price_elec; }
    double get_price_diesel()       const { return price_diesel; }
    double get_hours_per_day()      const { return hours_per_day; }
    double get_wage_semi()          const { return wage_semi; }
    double get_wage_heavy()         const { return wage_heavy; }


  private:
    double _overload_penalty_factor        = 3.0;
    double _range_excess_penalty_factor    = 3.0;
    double _worktime_penalty_factor        = 1.5;

  public:
    HFVRPEvaluation(py::list veh_props, resource_t max_work_time_sec, py::dict city)
        : max_work_time(max_work_time_sec) {
        num_veh = py::len(veh_props);
        acq.resize(num_veh);
        cap_w.resize(num_veh);
        cap_v.resize(num_veh);
        rng.resize(num_veh);
        for (size_t i = 0; i < num_veh; ++i) {
            auto t       = veh_props[i].cast<py::tuple>();
            acq[i]  = t[0].cast<resource_t>();
            cap_w[i]= t[1].cast<resource_t>();
            cap_v[i]= t[2].cast<resource_t>();
            rng[i]  = t[3].cast<resource_t>();
        }

        /* ------- grab seven floats from the dict ---------------- */
        auto get = [&](const char* key, double dflt = 0.0) -> resource_t {
            return city.contains(key) ? city[key].cast<double>()
                                      : static_cast<resource_t>(dflt);
        };
        utility_other    = get("utility_other");
        maintenance_cost = get("maintenance_cost");
        price_elec       = get("price_elec");
        price_diesel     = get("price_diesel");
        hours_per_day    = get("hours_per_day", 8.0);
        wage_semi        = get("wage_semi");
        wage_heavy       = get("wage_heavy");
    }

  private:
    cost_t _compute_cost_for_vehicle_id(size_t k,
                                        resource_t dist, resource_t w,
                                        resource_t v, resource_t t) const {
        auto ow = std::max<resource_t>(0, w - cap_w[k]);
        auto ov = std::max<resource_t>(0, v - cap_v[k]);
        auto orng = std::max<resource_t>(0, dist - rng[k]);
        auto ot   = std::max<resource_t>(0, t - max_work_time);
        return dist
               + acq[k]
               + ow * pen_over + ov * pen_over
               + orng * pen_range
               + ot   * pen_time;
    }

    std::pair<size_t, cost_t>
    _best_vehicle(resource_t d, resource_t w, resource_t v, resource_t t) const {
        size_t best = 0;
        auto bestc = _compute_cost_for_vehicle_id(0, d, w, v, t);
        for (size_t k = 1; k < num_veh; ++k) {
            auto c = _compute_cost_for_vehicle_id(k, d, w, v, t);
            if (c < bestc) { bestc = c; best = k; }
        }
        return {best, bestc};
    }

  public:
    /* ---- mandatory overrides ------------------------------------------- */

    cost_t concatenate(const HFVRP_forward_label& f,
                       const HFVRP_backward_label& b,
                       const routingblocks::Vertex& pred,
                       const HFVRP_vertex_data& pred_dat) {

        auto [vid, var_cost] = _best_vehicle(f.distance+b.distance,
                                         f.load_weight+b.load_weight,
                                         f.load_volume+b.load_volume,
                                         f.work_time +b.work_time);


        // Charge the fixed costs *only* when we leave the depot (pred.is_depot)
        cost_t fixed = 0;
        if (pred.is_depot) {
            auto wage = (cap_w[vid] > 3500 ? wage_heavy : wage_semi);
            fixed = utility_other + maintenance_cost + wage;
        }
        return var_cost + fixed;
    }

    std::vector<resource_t>
    get_cost_components(const HFVRP_forward_label& f) const {
        auto k = _best_vehicle(f.distance, f.load_weight,
                               f.load_volume, f.work_time).first;
        return {f.distance,
                std::max<resource_t>(0, f.distance   - rng[k]),
                std::max<resource_t>(0, f.load_weight- cap_w[k]),
                std::max<resource_t>(0, f.load_volume- cap_v[k]),
                std::max<resource_t>(0, f.work_time  - max_work_time)};
    }

    cost_t compute_cost(const HFVRP_forward_label& f) const {
        return _best_vehicle(f.distance, f.load_weight,
                             f.load_volume, f.work_time).second;
    }

    bool is_feasible(const HFVRP_forward_label& f) const {
        auto k = _best_vehicle(f.distance, f.load_weight,
                               f.load_volume, f.work_time).first;
        return f.load_weight <= cap_w[k] && f.load_volume <= cap_v[k]
               && f.distance <= rng[k]   && f.work_time <= max_work_time;
    }

    size_t compute_best_vehicle_id_of_route(
        const routingblocks::Route& r) const {
        const auto& f = r.end_depot().operator*().forward_label().get<HFVRP_forward_label>();
        return _best_vehicle(f.distance, f.load_weight,
                             f.load_volume, f.work_time).first;
    }

    public:
        py::dict summarize_route(const routingblocks::Route& route) const {
            const auto& label = route.end_depot().operator*().forward_label().get<HFVRP_forward_label>();
            auto vid = _best_vehicle(label.distance, label.load_weight, label.load_volume, label.work_time).first;
            auto cost = _compute_cost_for_vehicle_id(vid, label.distance, label.load_weight, label.load_volume, label.work_time);

            py::dict result;
            result["vehicle_type"] = vid;
            result["cost"] = cost;
            result["distance"] = label.distance;
            result["duration"] = label.work_time;
            result["load_weight"] = label.load_weight;
            result["load_volume"] = label.load_volume;
            result["capacity_weight"] = cap_w[vid];
            result["capacity_volume"] = cap_v[vid];
            return result;
        }


    /* ---- label propagation -------------------------------------------- */

    HFVRP_forward_label propagate_forward(
        const HFVRP_forward_label& p,
        const routingblocks::Vertex&, const HFVRP_vertex_data&,
        const routingblocks::Vertex& v, const HFVRP_vertex_data& vdat,
        const routingblocks::Arc&, const HFVRP_arc_data& ad) const {

        return {p.distance + ad.distance,
                p.load_weight + vdat.demand_weight,
                p.load_volume + vdat.demand_volume,
                p.work_time   + ad.travel_time
                              + (v.is_depot ? 0 : SERVICE_SEC)};
    }

    HFVRP_backward_label propagate_backward(
        const HFVRP_backward_label& s,
        const routingblocks::Vertex&, const HFVRP_vertex_data& sdat,
        const routingblocks::Vertex&,
        const HFVRP_vertex_data&, const routingblocks::Arc&,
        const HFVRP_arc_data& ad) const {

        return {s.distance + ad.distance,
                s.load_weight + sdat.demand_weight,
                s.load_volume + sdat.demand_volume,
                s.work_time   + ad.travel_time + SERVICE_SEC};
    }

    HFVRP_forward_label create_forward_label(
        const routingblocks::Vertex& v, const HFVRP_vertex_data& d) {
        return {0, d.demand_weight, d.demand_volume,
                v.is_depot ? 0 : SERVICE_SEC};
    }
    HFVRP_backward_label create_backward_label(
        const routingblocks::Vertex&, const HFVRP_vertex_data&) {
        return {0, 0, 0, 0};
    }
};

/* -------------------------  Python binding ----------------------------- */

PYBIND11_MODULE(_routingblocks_bais_as, m)
{
    pybind11::module_::import("routingblocks._routingblocks");

    // Version string that setup.py / CMake passes in
    m.attr("__version__") = PREPROCESSOR_TO_STRING(ROUTINGBLOCKS_EXT_MODULE_VERSION);

    /* --------------------------------------------------------------
       1)  Register the *abstract* C++ base so Python knows it exists
    -------------------------------------------------------------- */

    py::class_<CityParams>(m, "CityParams")
    .def(py::init<resource_t,resource_t,resource_t,
                  resource_t,resource_t,resource_t,resource_t>());

    /* --------------------------------------------------------------
       2)  Small helper structs that travel through the algorithm
    -------------------------------------------------------------- */
    py::class_<HFVRP_vertex_data>(m, "HFVRPVertexData")
    .def(py::init<resource_t, resource_t>(),
         py::arg("demand_weight") = 0.0,
         py::arg("demand_volume") = 0.0)
    .def_readonly("demand_weight", &HFVRP_vertex_data::demand_weight)
    .def_readonly("demand_volume", &HFVRP_vertex_data::demand_volume);

    py::class_<HFVRP_arc_data>(m, "HFVRPArcData")
        .def(py::init<resource_t, resource_t>(),
             py::arg("distance"), py::arg("travel_time"))
        .def_property_readonly("distance",
             [](const HFVRP_arc_data& a){ return a.distance; })
        .def_property_readonly("travel_time",
             [](const HFVRP_arc_data& a){ return a.travel_time; });

    py::class_<HFVRP_forward_label>(m, "HFVRPForwardLabel")
        .def_property_readonly("distance",    [](const HFVRP_forward_label& l){ return l.distance; })
        .def_property_readonly("load_weight", [](const HFVRP_forward_label& l){ return l.load_weight; })
        .def_property_readonly("load_volume", [](const HFVRP_forward_label& l){ return l.load_volume; })
        .def_property_readonly("work_time",   [](const HFVRP_forward_label& l){ return l.work_time; });

    py::class_<HFVRP_backward_label>(m, "HFVRPBackwardLabel")
        .def_property_readonly("distance",    [](const HFVRP_backward_label& l){ return l.distance; })
        .def_property_readonly("load_weight", [](const HFVRP_backward_label& l){ return l.load_weight; })
        .def_property_readonly("load_volume", [](const HFVRP_backward_label& l){ return l.load_volume; })
        .def_property_readonly("work_time",   [](const HFVRP_backward_label& l){ return l.work_time; });

    /* --------------------------------------------------------------
       3)  Evaluation class itself
    -------------------------------------------------------------- */
    py::class_<HFVRPEvaluation, routingblocks::Evaluation>(m, "HFVRPEvaluation")
        .def(py::init<py::list, resource_t, py::dict>(),
             py::arg("vehicle_properties"),
             py::arg("max_work_time_sec"),
             py::arg("city_params"))
        .def("concatenate",                     &HFVRPEvaluation::concatenate)
        .def("compute_cost",                    &HFVRPEvaluation::compute_cost)
        .def("compute_best_vehicle_id_of_route",&HFVRPEvaluation::compute_best_vehicle_id_of_route)
        .def("is_feasible",                     &HFVRPEvaluation::is_feasible)
        .def("get_cost_components",             &HFVRPEvaluation::get_cost_components)
        .def("propagate_forward",               &HFVRPEvaluation::propagate_forward)
        .def("propagate_backward",              &HFVRPEvaluation::propagate_backward)
        .def("create_forward_label",            &HFVRPEvaluation::create_forward_label)
        .def("create_backward_label",           &HFVRPEvaluation::create_backward_label)
        .def("summarize_route",                 &HFVRPEvaluation::summarize_route)
        .def_property_readonly("utility_other",   &HFVRPEvaluation::get_utility_other)
        .def_property_readonly("maintenance_cost",&HFVRPEvaluation::get_maintenance_cost)
        .def_property_readonly("price_elec",      &HFVRPEvaluation::get_price_elec)
        .def_property_readonly("price_diesel",    &HFVRPEvaluation::get_price_diesel)
        .def_property_readonly("hours_per_day",   &HFVRPEvaluation::get_hours_per_day)
        .def_property_readonly("wage_semi",       &HFVRPEvaluation::get_wage_semi)
        .def_property_readonly("wage_heavy",      &HFVRPEvaluation::get_wage_heavy)
        .def_readonly("cap_w", &HFVRPEvaluation::cap_w)
        .def_readonly("cap_v", &HFVRPEvaluation::cap_v)
        /* tunable penalty factors */
        .def_property("overload_penalty_factor",
             &HFVRPEvaluation::get_overload_penalty_factor,
             &HFVRPEvaluation::set_overload_penalty_factor)
        .def_property("range_excess_penalty_factor",
             &HFVRPEvaluation::get_range_excess_penalty_factor,
             &HFVRPEvaluation::set_range_excess_penalty_factor)
        .def_property("worktime_penalty_factor",
             &HFVRPEvaluation::get_worktime_penalty_factor,
             &HFVRPEvaluation::set_worktime_penalty_factor);

    /* --------------------------------------------------------------
       4)  Convenience C-helpers for building vertices/arcs from Python
    -------------------------------------------------------------- */
    m.def("create_hfvrp_vertex",
          &bindings::helpers::vertex_constructor<HFVRP_vertex_data>);
    m.def("create_hfvrp_arc",
          &bindings::helpers::arc_constructor<HFVRP_arc_data>);
}