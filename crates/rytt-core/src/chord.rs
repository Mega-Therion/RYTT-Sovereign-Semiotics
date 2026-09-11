//! Dual-plane radial chord types.

/// Radial plane. `z = 0` anchors lowercase, `z = 25` anchors uppercase.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum Plane {
    Lower,
    Upper,
}

impl Plane {
    pub fn z(self) -> u8 {
        match self {
            Plane::Lower => 0,
            Plane::Upper => 25,
        }
    }
}

/// A discrete radial chord: plane, angular index, and ring.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub struct Chord {
    pub plane: Plane,
    pub angle: u8,
    pub ring: u8,
}
