//! Security primitives — spec section 4.1 (hardened external face).
//!
//! Currently provides a lightweight per-IP rate limiter used to protect the
//! chat handler from abusive clients.

use std::time::{Duration, Instant};

use dashmap::DashMap;

/// Per-IP fixed-window rate limiter.
///
/// Each client IP gets a counter and a window-start timestamp. When the
/// configured window elapses the counter resets on the next request. This is
/// a fixed-window strategy: simple, allocation-light and good enough for a
/// coarse abuse guard. It is not a precise sliding window.
pub struct RateLimiter {
    /// Maximum number of requests permitted per window, per IP.
    max_requests: u32,
    /// Length of the counting window.
    window: Duration,
    /// Per-IP state: (window start, request count within that window).
    buckets: DashMap<String, (Instant, u32)>,
}

impl RateLimiter {
    /// Builds a rate limiter allowing `max_requests` per `window`.
    pub fn new(max_requests: u32, window: Duration) -> Self {
        Self {
            max_requests,
            window,
            buckets: DashMap::new(),
        }
    }

    /// Convenience constructor: `max_requests` per 60-second window.
    pub fn per_minute(max_requests: u32) -> Self {
        Self::new(max_requests, Duration::from_secs(60))
    }

    /// Records a request from `ip` and reports whether it is allowed.
    ///
    /// Returns `true` when the request is within the limit, `false` when the
    /// IP has exceeded `max_requests` in the current window. A `false` result
    /// does not consume further budget — the window must elapse to reset.
    pub fn check(&self, ip: &str) -> bool {
        self.check_at(ip, Instant::now())
    }

    /// Same as [`check`](Self::check) but with an explicit "now", which keeps
    /// the time-window behaviour deterministically testable.
    pub fn check_at(&self, ip: &str, now: Instant) -> bool {
        let mut entry = self
            .buckets
            .entry(ip.to_string())
            .or_insert((now, 0));
        let (window_start, count) = &mut *entry;

        // Reset the window if it has elapsed since this IP's first request.
        if now.duration_since(*window_start) >= self.window {
            *window_start = now;
            *count = 0;
        }

        if *count >= self.max_requests {
            return false;
        }
        *count += 1;
        true
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn under_limit_requests_are_allowed() {
        let limiter = RateLimiter::new(5, Duration::from_secs(60));
        // All five requests within the budget must be permitted.
        for _ in 0..5 {
            assert!(limiter.check("10.0.0.1"));
        }
    }

    #[test]
    fn over_limit_requests_are_blocked() {
        let limiter = RateLimiter::new(3, Duration::from_secs(60));
        // The first three requests pass.
        assert!(limiter.check("10.0.0.2"));
        assert!(limiter.check("10.0.0.2"));
        assert!(limiter.check("10.0.0.2"));
        // The fourth and beyond are rejected.
        assert!(!limiter.check("10.0.0.2"));
        assert!(!limiter.check("10.0.0.2"));
    }

    #[test]
    fn window_resets_after_elapsed_time() {
        let limiter = RateLimiter::new(2, Duration::from_secs(60));
        let t0 = Instant::now();

        // Exhaust the budget at t0.
        assert!(limiter.check_at("10.0.0.3", t0));
        assert!(limiter.check_at("10.0.0.3", t0));
        assert!(!limiter.check_at("10.0.0.3", t0));

        // Still blocked just before the window closes.
        assert!(!limiter.check_at("10.0.0.3", t0 + Duration::from_secs(59)));

        // Once the full window has elapsed the counter resets.
        let t1 = t0 + Duration::from_secs(60);
        assert!(limiter.check_at("10.0.0.3", t1));
        assert!(limiter.check_at("10.0.0.3", t1));
        assert!(!limiter.check_at("10.0.0.3", t1));
    }

    #[test]
    fn distinct_ips_have_independent_budgets() {
        let limiter = RateLimiter::new(1, Duration::from_secs(60));
        // Each IP gets its own bucket.
        assert!(limiter.check("1.1.1.1"));
        assert!(!limiter.check("1.1.1.1"));
        assert!(limiter.check("2.2.2.2"));
        assert!(!limiter.check("2.2.2.2"));
    }
}
