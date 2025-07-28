#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
namespace py = pybind11;                 // NEW  ← lets us write py::arg()

#include <vector>
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


struct FleetRow {                     // ❶  keep type code for printing
    std::string typ;
    resource_t  cnt;
    resource_t  cap_w, cap_v;
    resource_t  acq, rng;
    resource_t  cons_kWh;
    resource_t  cons_l;
    resource_t  maint_km;
};
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
    resource_t inside_km;
    resource_t load_weight;
    resource_t load_volume;
    resource_t work_time;

    HFVRP_forward_label(resource_t d, resource_t in, resource_t w, resource_t v,
                        resource_t t)
        : distance(d), inside_km(in), load_weight(w), load_volume(v), work_time(t) {}
};

struct HFVRP_backward_label {
    resource_t distance;
    resource_t inside_km;
    resource_t load_weight;
    resource_t load_volume;
    resource_t work_time;

    HFVRP_backward_label(resource_t d, resource_t in, resource_t w, resource_t v,
                         resource_t t)
        : distance(d), inside_km(in), load_weight(w), load_volume(v), work_time(t) {}
};

struct HFVRP_vertex_data {
    resource_t demand_weight;
    resource_t demand_volume;
    resource_t service_time;
    HFVRP_vertex_data(resource_t w, resource_t v, resource_t s)
        : demand_weight(w), demand_volume(v), service_time(s) {}
};

struct HFVRP_arc_data {
    resource_t distance;
    resource_t travel_time;
    resource_t inside_km;
    HFVRP_arc_data(resource_t d, resource_t t, resource_t in) : distance(d), travel_time(t), inside_km(in) {}
};

struct CostBreakdown {
    cost_t fuel_cost;
    cost_t maint_cost;
    cost_t wage_cost;
    cost_t toll_cost;
    cost_t amortized_acq_cost;
    cost_t green_upside_cost_discount;
    cost_t total;

    py::dict to_dict() const {
        py::dict d;
        d["fuel_cost"] = fuel_cost;
        d["maint_cost"] = maint_cost;
        d["wage_cost"] = wage_cost;
        d["toll_cost"] = toll_cost;
        d["amortized_acq_cost"] = amortized_acq_cost;
        d["green_upside_cost_discount"] = green_upside_cost_discount;
        d["total"] = total;
        return d;
    }
};

class HFVRPEvaluation
        : public routingblocks::ConcatenationBasedEvaluationImpl<
              HFVRPEvaluation, HFVRP_forward_label, HFVRP_backward_label,
              HFVRP_vertex_data, HFVRP_arc_data> {
  std::vector<FleetRow> _fleet;
  resource_t            _max_work_time;
  resource_t toll_per_km_inside = 0.0;
  // storing how many vehicles of each type are in the initial fleet
  std::unordered_map<std::string, int> _initial_fleet_count;
  // tracking how many vehicles of each type are used in the solution

  public:
    std::vector<std::string> _typ;
    std::vector<resource_t> acq, cap_w, cap_v,
                            rng, cons_kWh, cons_l, maint_km;
    enum CostComponent { DIST = 0, RANGE = 1, OVER_W = 2,
                         OVER_V = 3, OVERTIME = 4, INSIDE_KM=5 };
    size_t choose_vehicle(resource_t dist,
                      resource_t inside_km,
                      resource_t load_w,
                      resource_t load_v,
                      resource_t work_t) const
    {
        return _best_vehicle(dist, inside_km, load_w, load_v, work_t, true).first;
    }

  private:
    int num_veh = 0;
    int num_initial_veh = 0;
    resource_t max_work_time = 0;
    resource_t utility_other     = 0.0;
    resource_t maintenance_cost  = 0.0;
    resource_t price_elec        = 0.0;
    resource_t price_diesel      = 0.0;
    resource_t hours_per_day     = 8.0;
    resource_t wage_semi         = 0.0;
    resource_t wage_heavy        = 0.0;
    resource_t revenue           = 0.0;
    resource_t green_upside      = 0.0;

    /* penalty factors */
    double _overload_penalty_factor        = 5.0; // per kg, per m^3 its 10 times that in cost function
    double _range_excess_penalty_factor    = 3.0;
    double _worktime_penalty_factor        = 0.01; // per second -> 36€ per hour overtime

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


  public:
    HFVRPEvaluation(py::list veh_props, py::list initial_veh_props, resource_t max_work_time_sec, py::dict city)
        : max_work_time(max_work_time_sec) {
        num_veh = py::len(veh_props);
        num_initial_veh = py::len(initial_veh_props);

        // fill initial fleet count
        for (size_t i = 0; i < num_initial_veh; ++i) {
            auto t = initial_veh_props[i].cast<py::tuple>();
            std::string typ = t[0].cast<std::string>();
            int count = 1;  // Each row represents 1 vehicle in solver logic
            _initial_fleet_count[typ] += count;
        }

        for (size_t i = 0; i < num_veh; ++i) {
            auto t = veh_props[i].cast<py::tuple>();

            FleetRow row;
            row.typ      = t[0].cast<std::string>();
            row.cnt       = 1;                           // ← keep 1; “cnt” isn’t used in the solver
            row.cap_v     = t[1].cast<resource_t>();
            row.cap_w     = t[2].cast<resource_t>();
            row.acq       = t[3].cast<resource_t>();
            row.cons_kWh  = t[4].cast<resource_t>();
            row.cons_l    = t[5].cast<resource_t>();
            row.rng       = t[6].cast<resource_t>();
            row.maint_km  = t[7].cast<resource_t>();

            _fleet.push_back(row);

            if (!_initial_fleet_count.contains(row.typ)) {
                _initial_fleet_count[row.typ] = 0;
            }            

            /* keep the per-vehicle vectors if you still need them somewhere
               else in the code — otherwise delete them. */
            acq.     push_back(row.acq);
            cap_w.   push_back(row.cap_w);
            cap_v.   push_back(row.cap_v);
            rng.     push_back(row.rng);
            cons_kWh.push_back(t[5].cast<resource_t>());
            cons_l.  push_back(t[6].cast<resource_t>());
            maint_km.push_back(t[7].cast<resource_t>());
        }

        /* ------- grab seven floats from the dict ---------------- */
        auto get = [&](const char* key, double dflt = 0.0) -> resource_t {
            return city.contains(key) ? city[key].cast<double>()
                                      : static_cast<resource_t>(dflt);
        };
        utility_other      = get("utility_other");
        maintenance_cost   = get("maintenance_cost");
        price_elec         = get("price_elec");
        price_diesel       = get("price_diesel");
        hours_per_day      = get("hours_per_day", 8.0);
        wage_semi          = get("wage_semi");
        wage_heavy         = get("wage_heavy");
        toll_per_km_inside = get("toll_per_km_inside", 0.0);
        revenue            = get("revenue");
        green_upside       = get("green_upside");
    }

  private:
    CostBreakdown _compute_cost_for_vehicle_id(size_t k,
                                        resource_t dist, resource_t inside_km, resource_t w,
                                        resource_t v, resource_t t, resource_t r, resource_t g) const {

        CostBreakdown c;
        /* --------- determine ICEV vs BEV by type -------------------- */
        const std::string& veh_type = _fleet[k].typ;
        const bool is_icev = (veh_type == "I" || veh_type == "II" ||
                              veh_type == "III");

        /* --------- acquisition cost -> TCO logic -------------------- */
        c.amortized_acq_cost = 0.0;
        bool is_used_from_initial = false;

        is_used_from_initial = (_initial_fleet_count.contains(veh_type) 
                                && _initial_fleet_count.at(veh_type) > 0);

        // Normal case: purchase, depreciated over 4 years
        constexpr double RESALE_ICEV = 0.5;
        constexpr double RESALE_BEV  = 0.45;
        constexpr int LIFETIME_YEARS = 4;
        constexpr int WORKDAYS_PER_YEAR = 250;
        constexpr int TOTAL_DAYS = LIFETIME_YEARS * WORKDAYS_PER_YEAR;

        if (!is_used_from_initial) {
            if (veh_type == "IV") {
                // Special case: leased vehicle (990€/month) with 250/12 working days per month
                c.amortized_acq_cost = 990.0 / 20.83;
            } else {
                const double resale_rate = is_icev ? RESALE_ICEV : RESALE_BEV;
                c.amortized_acq_cost = (_fleet[k].acq * (1.0 - resale_rate)) / TOTAL_DAYS;
            }
        }

        /* --------- variable costs ----------------------------------- */
        c.fuel_cost =
            _fleet[k].cons_l  * price_diesel * dist +        // diesel
            _fleet[k].cons_kWh* price_elec   * dist;         // electricity (if BEV)
        c.maint_cost = _fleet[k].maint_km * dist;

        // wage €/h  (JSON already gives €/h)
        const auto wage_rate = (_fleet[k].cap_w > 3500 ? wage_heavy : wage_semi);
        c.wage_cost = (t / 3600.0) * wage_rate;          // t is seconds

        // toll
        c.toll_cost = is_icev ? inside_km * toll_per_km_inside : 0.0;

        // gree upside
        c.green_upside_cost_discount = (num_initial_veh > 0)
                                        ? (revenue * green_upside) / (WORKDAYS_PER_YEAR * num_initial_veh)
                                        : 0.0;

        /* --------- penalties / overload ----------------------------- */
        auto ow   = std::max<resource_t>(0, w - _fleet[k].cap_w);
        auto ov   = std::max<resource_t>(0, v - _fleet[k].cap_v);
        auto orng = std::max<resource_t>(0, dist - _fleet[k].rng);
        auto ot   = std::max<resource_t>(0, t - max_work_time);

        /* --------- total -------------------------------------------- */
        c.total = c.fuel_cost + c.maint_cost + c.wage_cost + c.toll_cost
              + c.amortized_acq_cost  // acq_c per day
              - c.green_upside_cost_discount // discount for a green vehicle
              + ow   * _overload_penalty_factor // penalties
              + ov   * _overload_penalty_factor * 10
              + orng * _range_excess_penalty_factor
              + ot   * _worktime_penalty_factor;

        return c;
    }

    std::pair<size_t, CostBreakdown>
    _best_vehicle(resource_t d, resource_t in, resource_t w, resource_t v, resource_t t, bool track_usage=true) const {
        size_t best = 0;
        CostBreakdown bestc = _compute_cost_for_vehicle_id(0, d, in, w, v, t, revenue, green_upside);
        for (size_t k = 1; k < num_veh; ++k) {
            CostBreakdown c = _compute_cost_for_vehicle_id(k, d, in, w, v, t, revenue, green_upside);
            if (c.total < bestc.total) { bestc = c; best = k; }
        }

        return {best, bestc};
    }
    

  public:
    /* ---- mandatory overrides ------------------------------------------- */

    cost_t concatenate(const HFVRP_forward_label& f,
                       const HFVRP_backward_label& b,
                       const routingblocks::Vertex& pred,
                       const HFVRP_vertex_data& pred_dat) {

        auto var_cost = _best_vehicle(f.distance+b.distance,
                                         f.inside_km+b.inside_km,
                                         f.load_weight+b.load_weight,
                                         f.load_volume+b.load_volume,
                                         f.work_time +b.work_time, false).second.total;

        cost_t fixed = pred.is_depot ? utility_other : 0.0;
        return var_cost + fixed;
    }

    std::vector<resource_t>
    get_cost_components(const HFVRP_forward_label& f) const {
        auto k = _best_vehicle(f.distance, f.inside_km, f.load_weight,
                               f.load_volume, f.work_time, false).first;
        return {f.distance, f.inside_km,
                std::max<resource_t>(0, f.distance   - _fleet[k].rng),
                std::max<resource_t>(0, f.load_weight- _fleet[k].cap_w),
                std::max<resource_t>(0, f.load_volume- _fleet[k].cap_v),
                std::max<resource_t>(0, f.work_time  - max_work_time)
                };
    }

    cost_t compute_cost(const HFVRP_forward_label& f) const {
        return _best_vehicle(f.distance, f.inside_km, f.load_weight,
                             f.load_volume, f.work_time, false).second.total;
    }

    bool is_feasible(const HFVRP_forward_label& f) const {
        auto k = _best_vehicle(f.distance, f.inside_km, f.load_weight,
                               f.load_volume, f.work_time, false).first;
        return f.load_weight <= _fleet[k].cap_w && f.load_volume <= _fleet[k].cap_v
               && f.distance <= _fleet[k].rng   && f.work_time <= max_work_time;
    }

    size_t compute_best_vehicle_id_of_route(
        const routingblocks::Route& r) const {
        const auto& f = r.end_depot().operator*().forward_label().get<HFVRP_forward_label>();
        return _best_vehicle(f.distance, f.inside_km, f.load_weight,
                             f.load_volume, f.work_time, false).first;
    }

    cost_t compute_resale_value_for_unused_vehicles(const std::vector<std::string>& vehicle_types_used) const {
        std::unordered_map<std::string, int> used;
    
        for (const auto& typ : vehicle_types_used) {
            used[typ]++;
        }
    
        cost_t resale_value = 0.0;
        for (const auto& [typ, init_count] : _initial_fleet_count) {
            int used_count = used.contains(typ) ? used.at(typ) : 0;
            int unused = std::max(0, init_count - used_count);
    
            const auto& row = *std::find_if(_fleet.begin(), _fleet.end(), [&](const FleetRow& r) {
                return r.typ == typ;
            });
    
            double resale_rate = (typ == "I" || typ == "II" || typ == "III") ? 0.5 : 0.45;
            resale_value += unused * row.acq * resale_rate;
        }
        return resale_value;
    }
    

    public:
        py::dict summarize_route(const routingblocks::Route& route) const {
            const auto& label = route.end_depot().operator*().forward_label().get<HFVRP_forward_label>();
            auto vid = _best_vehicle(label.distance, label.inside_km, label.load_weight, label.load_volume, label.work_time, false).first;
            CostBreakdown c = _compute_cost_for_vehicle_id(vid, label.distance, label.inside_km, label.load_weight, label.load_volume, label.work_time, this->revenue, this->green_upside);

            cost_t fixed = (route.size() > 2) ? utility_other : 0.0;

            py::dict result;
            result["vehicle_type"] = _fleet[vid].typ;    // e.g. "I"
            result["fixed_cost"] = fixed;
            result["cost"] = c.total + fixed;
            result["distance"] = label.distance;
            result["duration"] = label.work_time;
            result["load_weight"] = label.load_weight;
            result["load_volume"] = label.load_volume;
            result["capacity_weight"] = _fleet[vid].cap_w;
            result["capacity_volume"] = _fleet[vid].cap_v;
            result["inside_km"] = label.inside_km;
            result["toll_cost"] = c.toll_cost;
            result["green_upside_cost_discount"] = c.green_upside_cost_discount;
            result["fuel_cost"] = c.fuel_cost;
            result["maint_cost"] = c.maint_cost;
            result["wage_cost"] = c.wage_cost;
            result["amortized_acq_cost"] = c.amortized_acq_cost;
            result["green_upside_cost_discount"] = c.green_upside_cost_discount;
            return result;
        }

    /* ---- label propagation -------------------------------------------- */

    HFVRP_forward_label propagate_forward(
        const HFVRP_forward_label& p,
        const routingblocks::Vertex&, const HFVRP_vertex_data&,
        const routingblocks::Vertex& v, const HFVRP_vertex_data& vdat,
        const routingblocks::Arc&, const HFVRP_arc_data& ad) const {

        return {p.distance + ad.distance,
                p.inside_km  + ad.inside_km,
                p.load_weight + vdat.demand_weight,
                p.load_volume + vdat.demand_volume,
                p.work_time   + ad.travel_time
                              + (v.is_depot ? 0 : vdat.service_time)};
    }

    HFVRP_backward_label propagate_backward(
        const HFVRP_backward_label& s,
        const routingblocks::Vertex&, const HFVRP_vertex_data& sdat,
        const routingblocks::Vertex&,
        const HFVRP_vertex_data&, const routingblocks::Arc&,
        const HFVRP_arc_data& ad) const {

        return {s.distance + ad.distance,
                s.inside_km  + ad.inside_km,
                s.load_weight + sdat.demand_weight,
                s.load_volume + sdat.demand_volume,
                s.work_time   + ad.travel_time + sdat.service_time};
    }

    HFVRP_forward_label create_forward_label(
        const routingblocks::Vertex& v, const HFVRP_vertex_data& d) {
        return {0, 0, d.demand_weight, d.demand_volume,
                v.is_depot ? 0 : d.service_time};
    }
    HFVRP_backward_label create_backward_label(
        const routingblocks::Vertex&, const HFVRP_vertex_data&) {
        return {0, 0, 0, 0, 0};
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
    .def(py::init<resource_t, resource_t, resource_t>(),
         py::arg("demand_weight") = 0.0,
         py::arg("demand_volume") = 0.0,
         py::arg("service_time")  = 0.0)
    .def_readonly("demand_weight", &HFVRP_vertex_data::demand_weight)
    .def_readonly("demand_volume", &HFVRP_vertex_data::demand_volume)
    .def_readonly("service_time",  &HFVRP_vertex_data::service_time);

    py::class_<HFVRP_arc_data>(m, "HFVRPArcData")
        .def(py::init<resource_t, resource_t, resource_t>(),
             py::arg("distance"), py::arg("travel_time"), py::arg("inside_km"))
        .def_property_readonly("distance",    [](const HFVRP_arc_data& a){ return a.distance; })
        .def_property_readonly("travel_time", [](const HFVRP_arc_data& a){ return a.travel_time; })
        .def_property_readonly("inside_km",   [](const HFVRP_arc_data& a){ return a.inside_km; });

    py::class_<HFVRP_forward_label>(m, "HFVRPForwardLabel")
        .def_property_readonly("distance",    [](const HFVRP_forward_label& l){ return l.distance; })
        .def_property_readonly("inside_km",   [](const HFVRP_forward_label& l){ return l.inside_km; })
        .def_property_readonly("load_weight", [](const HFVRP_forward_label& l){ return l.load_weight; })
        .def_property_readonly("load_volume", [](const HFVRP_forward_label& l){ return l.load_volume; })
        .def_property_readonly("work_time",   [](const HFVRP_forward_label& l){ return l.work_time; });

    py::class_<HFVRP_backward_label>(m, "HFVRPBackwardLabel")
        .def_property_readonly("distance",    [](const HFVRP_backward_label& l){ return l.distance; })
        .def_property_readonly("inside_km",   [](const HFVRP_backward_label& l){ return l.inside_km; })
        .def_property_readonly("load_weight", [](const HFVRP_backward_label& l){ return l.load_weight; })
        .def_property_readonly("load_volume", [](const HFVRP_backward_label& l){ return l.load_volume; })
        .def_property_readonly("work_time",   [](const HFVRP_backward_label& l){ return l.work_time; });

    /* --------------------------------------------------------------
       3)  Evaluation class itself
    -------------------------------------------------------------- */
    py::class_<HFVRPEvaluation, routingblocks::Evaluation>(m, "HFVRPEvaluation")
        .def(py::init<py::list, py::list, resource_t, py::dict>(),
             py::arg("vehicle_properties"),
             py::arg("initial_vehicle_properties"),
             py::arg("max_work_time_sec"),
             py::arg("city_params"))
        .def("choose_vehicle", &HFVRPEvaluation::choose_vehicle,
             py::arg("inside_km"),
             py::arg("distance"),
             py::arg("load_weight"),
             py::arg("load_volume"),
             py::arg("work_time"))
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
             &HFVRPEvaluation::set_worktime_penalty_factor)
        .def("compute_resale_value_for_unused_vehicles", &HFVRPEvaluation::compute_resale_value_for_unused_vehicles);


    /* --------------------------------------------------------------
       4)  Convenience C-helpers for building vertices/arcs from Python
    -------------------------------------------------------------- */
    m.def("create_hfvrp_vertex",
          &bindings::helpers::vertex_constructor<HFVRP_vertex_data>);
    m.def("create_hfvrp_arc",
          &bindings::helpers::arc_constructor<HFVRP_arc_data>);
}