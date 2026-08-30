# Day planning

Detail only the selected route. Each day needs a thesis, primary timeline, travel/load, hard cutoffs and buffers, latest switch point, meal and booking context, weather-aware backup without a base change, and linked sources/statuses. Keep alternatives visible as alternatives; do not write a view-only scenario choice back into canonical state.

The canonical schedule shape is `days[].timeline[]`. Give every timeline entry an `id`; keep `time` as the human label, and record offset-bearing `start_at`/`end_at`, operating or service cutoffs, component minutes, connection minimums, and buffer markers on that same entry only when those values are explicitly known. Link an overnight to its canonical `route_stops[].id` with `overnight_stop_id`; do not create parallel top-level interval, leg, connection, or stay collections.

Use local times for every transport segment and record door-to-door duration, connections, luggage/storage, reservation need, cost basis, and comfortable/budget alternatives. A map link provides place context but never replaces an official timetable.

If a user changes a restaurant, activity, hotel, flight, traveller constraint, or route element, say what will be recalculated first. Update the smallest affected canonical scope, preserve untouched days, and run the appropriate challenge again. A frozen structural change still needs impact analysis and explicit consent.
