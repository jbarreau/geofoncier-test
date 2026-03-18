# CHANGELOG

<!-- version list -->

## v1.1.0 (2026-03-18)

### Bug Fixes

- **analytics**: Fix ApexCharts toolbar CSS conflict with PicoCSS
  ([#27](https://github.com/jbarreau/geofoncier-test/pull/27),
  [`687402f`](https://github.com/jbarreau/geofoncier-test/commit/687402f58dc0b4ac170520c5e0a966f734b1f08e))

- **analytics**: Fix download menu layout broken by overly broad CSS rule
  ([#27](https://github.com/jbarreau/geofoncier-test/pull/27),
  [`687402f`](https://github.com/jbarreau/geofoncier-test/commit/687402f58dc0b4ac170520c5e0a966f734b1f08e))

- **analytics**: Fix NaN labels, CSS toolbar buttons, spread mock task dates
  ([#27](https://github.com/jbarreau/geofoncier-test/pull/27),
  [`687402f`](https://github.com/jbarreau/geofoncier-test/commit/687402f58dc0b4ac170520c5e0a966f734b1f08e))

- **analytics**: Fix toolbar icon buttons without breaking download menu
  ([#27](https://github.com/jbarreau/geofoncier-test/pull/27),
  [`687402f`](https://github.com/jbarreau/geofoncier-test/commit/687402f58dc0b4ac170520c5e0a966f734b1f08e))

- **mock**: Add coherent updated_at to task seed data
  ([#27](https://github.com/jbarreau/geofoncier-test/pull/27),
  [`687402f`](https://github.com/jbarreau/geofoncier-test/commit/687402f58dc0b4ac170520c5e0a966f734b1f08e))

### Features

- **analytics**: Add analytics page with ApexCharts
  ([#27](https://github.com/jbarreau/geofoncier-test/pull/27),
  [`687402f`](https://github.com/jbarreau/geofoncier-test/commit/687402f58dc0b4ac170520c5e0a966f734b1f08e))

- **analytics**: Add over-time endpoint ([#27](https://github.com/jbarreau/geofoncier-test/pull/27),
  [`687402f`](https://github.com/jbarreau/geofoncier-test/commit/687402f58dc0b4ac170520c5e0a966f734b1f08e))

- **analytics**: Show user email instead of UUID in by-user chart
  ([#27](https://github.com/jbarreau/geofoncier-test/pull/27),
  [`687402f`](https://github.com/jbarreau/geofoncier-test/commit/687402f58dc0b4ac170520c5e0a966f734b1f08e))

- **home**: Add analytics card on home page
  ([#27](https://github.com/jbarreau/geofoncier-test/pull/27),
  [`687402f`](https://github.com/jbarreau/geofoncier-test/commit/687402f58dc0b4ac170520c5e0a966f734b1f08e))

### Testing

- **analytics**: Add full test coverage for analytics feature
  ([#27](https://github.com/jbarreau/geofoncier-test/pull/27),
  [`687402f`](https://github.com/jbarreau/geofoncier-test/commit/687402f58dc0b4ac170520c5e0a966f734b1f08e))


## v1.0.2 (2026-03-18)

### Bug Fixes

- **e2e**: Update DB DSN to target postgres-auth after DB split
  ([#24](https://github.com/jbarreau/geofoncier-test/pull/24),
  [`4d4d176`](https://github.com/jbarreau/geofoncier-test/commit/4d4d1766027e03cb34e38b320e09974b31e55cda))

### Chores

- **infra**: Split mock-data into mock-users and mock-tasks
  ([#24](https://github.com/jbarreau/geofoncier-test/pull/24),
  [`4d4d176`](https://github.com/jbarreau/geofoncier-test/commit/4d4d1766027e03cb34e38b320e09974b31e55cda))

- **infra**: Split PostgreSQL into two independent instances per service
  ([#24](https://github.com/jbarreau/geofoncier-test/pull/24),
  [`4d4d176`](https://github.com/jbarreau/geofoncier-test/commit/4d4d1766027e03cb34e38b320e09974b31e55cda))

### Testing

- **frontend**: Add test suite with 98% coverage
  ([#26](https://github.com/jbarreau/geofoncier-test/pull/26),
  [`d1f04e0`](https://github.com/jbarreau/geofoncier-test/commit/d1f04e02bac26f7229c1f01897afc9f20ee11519))


## v1.0.1 (2026-03-18)

### Chores

- Quick update on claude.md ([#23](https://github.com/jbarreau/geofoncier-test/pull/23),
  [`8c1a687`](https://github.com/jbarreau/geofoncier-test/commit/8c1a687b6a697862c7c5d0e709970c276fdb1c0d))

### Refactoring

- **structure**: Reorganize monorepo layout and add frontend coverage
  ([#23](https://github.com/jbarreau/geofoncier-test/pull/23),
  [`8c1a687`](https://github.com/jbarreau/geofoncier-test/commit/8c1a687b6a697862c7c5d0e709970c276fdb1c0d))


## v1.0.0 (2026-03-18)

- Initial Release
