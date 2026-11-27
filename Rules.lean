import Std

namespace Terachess

inductive Side where | white | black
  deriving DecidableEq, Repr

def Side.other : Side → Side
  | .white => .black
  | .black => .white

def Side.forward : Side → Int
  | .white => 1
  | .black => -1

@[simp] theorem Side.other_other (s : Side) : s.other.other = s := by cases s <;> rfl
@[simp] theorem Side.other_ne (s : Side) : s.other ≠ s := by cases s <;> decide

inductive Kind where
  | amazon | bishop | cannon | duchess | elephant | buffalo | eagle
  | marshall | prince | centaur | king | lion | camel | knight | sorceress
  | pawn | queen | rook | admiral | troll | rhinoceros | archer | machine
  | cardinal | missionary | giraffe
  deriving DecidableEq, Repr

structure Piece where
  side : Side
  kind : Kind
  deriving DecidableEq, Repr

abbrev Square := Fin 16 × Fin 16
abbrev Board := Square → Option Piece

structure Move where
  src : Square
  dst : Square
  deriving DecidableEq, Repr

structure Position where
  board : Board
  turn : Side
  king : Side → Square
  jump : Side → Bool
  ep : Option Square
  halfmove : Nat
  fullmove : Nat

def squares : List Square :=
  (List.finRange 16).flatMap fun y => (List.finRange 16).map fun x => (x, y)

theorem fin_mem (i : Fin 16) : i ∈ List.finRange 16 := by
  have bound : i.val < (List.finRange 16).length := by simp
  have h := List.getElem_mem (l := List.finRange 16) bound
  simpa using h

theorem square_mem (s : Square) : s ∈ squares := by
  rcases s with ⟨x, y⟩
  exact List.mem_flatMap.mpr ⟨y, fin_mem y, List.mem_map.mpr ⟨x, fin_mem x, rfl⟩⟩

def dx (m : Move) : Int := (m.dst.1.val : Int) - m.src.1.val
def dy (m : Move) : Int := (m.dst.2.val : Int) - m.src.2.val
def distance (m : Move) := max (dx m).natAbs (dy m).natAbs
def small (m : Move) := min (dx m).natAbs (dy m).natAbs

def shift (s : Square) (x y : Int) : Option Square :=
  let a := (s.1.val : Int) + x
  let b := (s.2.val : Int) + y
  if ha : 0 ≤ a ∧ a < 16 then
    if hb : 0 ≤ b ∧ b < 16 then
      some (⟨a.toNat, by omega⟩, ⟨b.toNat, by omega⟩)
    else none
  else none

def rankLast : Side → Fin 16
  | .white => 15
  | .black => 0

def home : Side → Square
  | .white => (7, 1)
  | .black => (7, 14)

def homePiece (rank : Nat) (file : Fin 16) : Option Kind :=
  let row : Array Kind := match rank with
  | 0 => #[.admiral, .centaur, .missionary, .marshall, .cardinal, .buffalo, .duchess,
           .sorceress, .sorceress, .duchess, .buffalo, .cardinal, .marshall,
           .missionary, .centaur, .admiral]
  | 1 => #[.cannon, .camel, .giraffe, .troll, .rhinoceros, .archer, .lion, .king,
           .amazon, .lion, .archer, .rhinoceros, .troll, .giraffe, .camel, .cannon]
  | 2 => #[.elephant, .rook, .knight, .bishop, .machine, .prince, .eagle, .queen,
           .queen, .eagle, .prince, .machine, .bishop, .knight, .rook, .elephant]
  | 3 => Array.replicate 16 .pawn
  | _ => #[]
  row[file.val]?

def initialBoard (q : Square) : Option Piece :=
  if q.2.val < 4 then (homePiece q.2.val q.1).map (Piece.mk .white)
  else (homePiece (15 - q.2.val) q.1).map (Piece.mk .black)

def initial : Position := ⟨initialBoard, .white, home, fun _ => true, none, 0, 1⟩

def orthogonal (m : Move) := decide (small m = 0 ∧ distance m > 0)
def diagonal (m : Move) := decide (small m = distance m ∧ distance m > 0)
def leap (m : Move) (a b : Nat) := decide (distance m = a ∧ small m = b)

def path (s : Square) (x y : Int) (count : Nat) : List (Option Square) :=
  (List.range count).map fun (i : Nat) => shift s (x * (Int.ofNat i + 1)) (y * (Int.ofNat i + 1))

def screens (board : Board) (pts : List (Option Square)) : Nat :=
  pts.countP fun sq => match sq with
    | none => true
    | some q => (board q).isSome

def ray (board : Board) (m : Move) (geometry : Bool) (n : Nat) : Bool :=
  geometry && decide (screens board (path m.src (dx m).sign (dy m).sign (distance m - 1)) = n)

def bent (b : Board) (m : Move) (eagle : Bool) : Bool :=
  let wide := (dy m).natAbs < (dx m).natAbs
  let x := (dx m).sign
  let y := (dy m).sign
  let a := if eagle || wide then x else 0
  let c := if eagle || !wide then y else 0
  let u := if eagle && !wide then 0 else x
  let v := if eagle && wide then 0 else y
  let shape := if eagle then small m == 1 else distance m == small m + 1
  shape && ((distance m == 1) ||
    match shift m.src a c with
    | none => false
    | some bend =>
        (b bend).isNone && screens b (path bend u v (distance m - 2)) == 0)

def diagonalForward (m : Move) (s : Side) : Bool :=
  (dx m).natAbs == 1 && dy m == s.forward

-- Capture geometry asks about a hypothetical enemy on the endpoint.
def geometry (b : Board) (s : Side) (k : Kind) (m : Move) (capture : Bool) : Bool :=
  let a := distance m
  let o := orthogonal m
  let d := diagonal m
  let r := ray b m
  let knight := leap m 2 1
  let camel := leap m 3 1
  let giraffe := leap m 3 2
  let pawnStep := if capture then diagonalForward m s else dx m == 0 && dy m == s.forward
  let doubleStep := !capture && dx m == 0 && dy m == 2 * s.forward &&
    (match shift m.src 0 s.forward with | some q => (b q).isNone | none => false)
  let screen := if capture then 1 else 0
  match k with
  | .amazon => r (o || d) 0 || knight
  | .bishop => r d 0
  | .cannon => r o screen
  | .duchess => (o || d) && a ≤ 3
  | .elephant => d && a ≤ 2
  | .buffalo => knight || camel || giraffe
  | .eagle => bent b m true
  | .marshall => r o 0 || knight
  | .prince => a == 1 || doubleStep
  | .centaur => a == 1 || knight
  | .king => a == 1
  | .lion => decide (0 < a ∧ a ≤ 2)
  | .camel => camel
  | .knight => knight
  | .sorceress => r (o || d) screen
  | .pawn => pawnStep || doubleStep
  | .queen => r (o || d) 0
  | .rook => r o 0
  | .admiral => r o 0 || (d && a == 1)
  | .troll => ((o || d) && a == 3) || pawnStep
  | .rhinoceros => bent b m false
  | .archer => r d screen
  | .machine => o && a ≤ 2
  | .cardinal => r d 0 || knight
  | .missionary => r d 0 || (o && a == 1)
  | .giraffe => giraffe

def attacked (b : Board) (bySide : Side) (target : Square) : Bool :=
  squares.any fun src =>
    match b src with
    | some p => p.side == bySide && geometry b bySide p.kind ⟨src, target⟩ true
    | none => false

def inCheck (p : Position) : Bool := attacked p.board p.turn.other (p.king p.turn)

def jumpMove (p : Position) (m : Move) : Bool :=
  let safe := fun sq => match sq with
    | some q => !(attacked p.board p.turn.other q)
    | none => false
  let x := (dx m).sign
  let y := (dy m).sign
  let a := if (dx m).natAbs == 2 then x else 0
  let b := if (dy m).natAbs == 2 then y else 0
  p.jump p.turn && distance m == 2 && (p.board m.dst).isNone && !inCheck p &&
    (safe (shift m.src x y) || safe (shift m.src a b))

def straightDouble (s : Side) (k : Kind) (m : Move) : Bool :=
  (k == .pawn || k == .prince) && dx m == 0 && dy m == 2 * s.forward

def victimKind (advancing : Side) (sq : Square) (k : Kind) : Prop :=
  if sq.2 = rankLast advancing then k = .queen ∨ k = .amazon
  else k = .pawn ∨ k = .prince

instance (s : Side) (sq : Square) (k : Kind) : Decidable (victimKind s sq k) := by
  unfold victimKind
  infer_instance

def victimSquare (m : Move) : Square := (m.dst.1, m.src.2)

def isVictim (b : Board) (s : Side) (sq : Square) : Bool :=
  match b sq with
  | some p => p.side == s && decide (victimKind s sq p.kind)
  | none => false

def epCapture (p : Position) (m : Move) (k : Kind) : Bool :=
  k == .pawn && p.ep == some m.dst && (p.board m.dst).isNone && diagonalForward m p.turn &&
    isVictim p.board p.turn.other (victimSquare m)

def takenAt (p : Position) (m : Move) (k : Kind) : Square :=
  if epCapture p m k then victimSquare m else m.dst

def promotedKind (k : Kind) (dist : Nat) : Kind :=
  match k with
  | .pawn => .queen
  | .prince => .amazon
  | .knight | .camel | .giraffe => .buffalo
  | .elephant | .machine | .centaur => .lion
  | .troll => if dist = 1 then .queen else .troll
  | k => k

def arriving (s : Side) (m : Move) (k : Kind) : Kind :=
  if m.dst.2 = rankLast s then promotedKind k (distance m) else k

def boardAfter (p : Position) (m : Move) (k : Kind) : Board := fun q =>
  if q = m.dst then some ⟨p.turn, arriving p.turn m k⟩
  else if q = m.src ∨ q = takenAt p m k then none
  else p.board q

def kingAfter (p : Position) (m : Move) (k : Kind) (s : Side) : Square :=
  if s = p.turn ∧ k = .king then m.dst else p.king s

def jumpAfter (p : Position) (k : Kind) (s : Side) : Bool :=
  if s = p.turn ∧ k = .king then false else p.jump s

def nextEP (p : Position) (m : Move) (k : Kind) : Option Square :=
  if straightDouble p.turn k m then shift m.src 0 p.turn.forward else none

def apply (p : Position) (m : Move) (k : Kind) : Position :=
  ⟨boardAfter p m k, p.turn.other, kingAfter p m k, jumpAfter p k, nextEP p m k,
   if k = .pawn ∨ (p.board (takenAt p m k)).isSome then 0 else p.halfmove + 1,
   if p.turn = .black then p.fullmove + 1 else p.fullmove⟩

def landing (p : Position) (q : Square) : Prop :=
  match p.board q with
  | none => True
  | some piece => piece.side ≠ p.turn ∧ piece.kind ≠ .king

instance (p : Position) (q : Square) : Decidable (landing p q) := by
  unfold landing
  split <;> infer_instance

-- Conditions are stated for an explicit piece kind and an explicit move.
def Conditions (p : Position) (m : Move) (k : Kind) : Prop :=
  m.src ≠ m.dst ∧ landing p m.dst ∧
  (geometry p.board p.turn k m (p.board m.dst).isSome = true ∨
   epCapture p m k = true ∨ (k = .king ∧ jumpMove p m = true)) ∧
  attacked (boardAfter p m k) p.turn.other (kingAfter p m k p.turn) = false

instance (p : Position) (m : Move) (k : Kind) : Decidable (Conditions p m k) := by
  unfold Conditions
  infer_instance

def Legal (p : Position) (m : Move) : Prop :=
  ∃ k, p.board m.src = some ⟨p.turn, k⟩ ∧ Conditions p m k

def accepts (p : Position) (m : Move) : Bool :=
  match p.board m.src with
  | none => false
  | some piece => piece.side == p.turn && decide (Conditions p m piece.kind)

def legalMoves (p : Position) : List Move :=
  squares.flatMap fun src =>
    match p.board src with
    | none => []
    | some piece => if piece.side = p.turn then
        (squares.map fun dst => Move.mk src dst).filter fun m =>
          decide (Conditions p m piece.kind)
      else []

theorem accepts_iff (p : Position) (m : Move) :
    accepts p m = true ↔ Legal p m := by
  cases h : p.board m.src with
  | none => simp [accepts, Legal, h]
  | some piece =>
    rcases piece with ⟨s, k⟩
    simp [accepts, Legal, h, and_assoc]

theorem generator_spec (p : Position) (m : Move) :
    m ∈ legalMoves p ↔ Legal p m := by
  unfold legalMoves
  constructor
  · intro h
    obtain ⟨src, _, hs⟩ := List.mem_flatMap.mp h
    cases he : p.board src with
    | none => simp [he] at hs
    | some piece =>
      by_cases ht : piece.side = p.turn
      · simp only [he, if_pos ht, List.mem_filter, decide_eq_true_eq] at hs
        obtain ⟨hm, hv⟩ := hs
        obtain ⟨dst, _, rfl⟩ := List.mem_map.mp hm
        exact ⟨piece.kind, by cases piece; simp_all, hv⟩
      · simp [he, ht] at hs
  · rintro ⟨k, hk, hv⟩
    apply List.mem_flatMap.mpr
    refine ⟨m.src, square_mem _, ?_⟩
    simp only [hk, if_true, List.mem_filter, decide_eq_true_eq]
    exact ⟨List.mem_map.mpr ⟨m.dst, square_mem _, by cases m <;> rfl⟩, hv⟩

theorem generator_sound (p : Position) (m : Move) :
    m ∈ legalMoves p → Legal p m := (generator_spec p m).mp

theorem generator_complete (p : Position) (m : Move) :
    Legal p m → m ∈ legalMoves p := (generator_spec p m).mpr

def step (p : Position) (m : Move) : Option Position :=
  if accepts p m then (p.board m.src).map fun piece => apply p m piece.kind else none

theorem step_exists_iff (p : Position) (m : Move) :
    (∃ q, step p m = some q) ↔ Legal p m := by
  constructor
  · rintro ⟨q, h⟩
    by_cases ok : accepts p m = true
    · exact (accepts_iff p m).mp ok
    · simp [step, ok] at h
  · intro h
    have ok := (accepts_iff p m).mpr h
    obtain ⟨k, hk, _⟩ := h
    exact ⟨apply p m k, by simp [step, ok, hk]⟩

def Kings (p : Position) : Prop :=
  ∀ s q, p.board q = some ⟨s, .king⟩ ↔ q = p.king s

def allowed (q : Square) (piece : Piece) : Prop :=
  q.2 = rankLast piece.side → piece.kind = .troll ∨ promotedKind piece.kind 1 = piece.kind

def PromotionRanks (p : Position) : Prop :=
  ∀ q piece, p.board q = some piece → allowed q piece

def JumpRights (p : Position) : Prop :=
  ∀ s, p.jump s = true → p.king s = home s

def PreviousRoyalSafe (p : Position) : Prop :=
  attacked p.board p.turn (p.king p.turn.other) = false

def EPValid (p : Position) : Prop :=
  ∀ e, p.ep = some e →
    ∃ origin dest, shift e 0 p.turn.forward = some origin ∧
      shift e 0 (-p.turn.forward) = some dest ∧
      p.board origin = none ∧ p.board e = none ∧ isVictim p.board p.turn.other dest = true

theorem landing_not_king {p : Position} {q : Square} (h : landing p q) (s : Side) :
    p.board q ≠ some ⟨s, .king⟩ := by
  intro atKing
  simp [landing, atKing] at h

theorem ep_not_king {p : Position} {m : Move} {k : Kind}
    (h : epCapture p m k = true) (s : Side) :
    p.board (victimSquare m) ≠ some ⟨s, .king⟩ := by
  intro atKing
  simp [epCapture, isVictim, atKing, victimKind] at h

theorem taken_not_king {p : Position} {m : Move} {k : Kind}
    (h : landing p m.dst) (s : Side) : p.board (takenAt p m k) ≠ some ⟨s, .king⟩ := by
  unfold takenAt
  split
  next he => exact ep_not_king he s
  next => exact landing_not_king h s

@[simp] theorem arriving_king_iff (s : Side) (m : Move) (k : Kind) :
    arriving s m k = .king ↔ k = .king := by
  unfold arriving
  split <;> cases k <;> simp [promotedKind] <;> split <;> simp

theorem kings_preserved {p : Position} {m : Move} {k : Kind}
    (kings : Kings p) (src : p.board m.src = some ⟨p.turn, k⟩)
    (rules : Conditions p m k) : Kings (apply p m k) := by
  have hsrc (s : Side) : m.src = p.king s ↔ p.turn = s ∧ k = .king := by
    rw [← kings s m.src, src]
    simp
  have hdst (s : Side) : m.dst ≠ p.king s :=
    fun eq => landing_not_king rules.2.1 s ((kings s m.dst).mpr eq)
  have htake (s : Side) : takenAt p m k ≠ p.king s :=
    fun eq => taken_not_king rules.2.1 s ((kings s _).mpr eq)
  intro s q
  change boardAfter p m k q = some ⟨s, .king⟩ ↔ q = kingAfter p m k s
  unfold boardAfter kingAfter
  by_cases mover : s = p.turn ∧ k = .king
  · have old : m.src = p.king s := (hsrc s).mpr ⟨mover.1.symm, mover.2⟩
    simp only [if_pos mover]
    by_cases dest : q = m.dst
    · simp [dest, mover.1, mover.2]
    · by_cases removed : q = m.src ∨ q = takenAt p m k
      · simp [dest, removed]
      · have different : q ≠ m.src := fun e => removed (Or.inl e)
        simp [dest, removed, kings s q, ← old, different]
  · simp only [if_neg mover]
    by_cases dest : q = m.dst
    · have different : ¬(p.turn = s ∧ k = .king) := fun h => mover ⟨h.1.symm, h.2⟩
      simp [dest, different, hdst s]
    · by_cases removed : q = m.src ∨ q = takenAt p m k
      · have different : q ≠ p.king s := by
          rcases removed with e | e
          · rw [e]
            exact fun h => mover ⟨((hsrc s).mp h).1.symm, ((hsrc s).mp h).2⟩
          · simpa [e] using htake s
        simp [dest, removed, different]
      · simp [dest, removed, kings s q]

theorem arriving_allowed (s : Side) (m : Move) (k : Kind) :
    allowed m.dst ⟨s, arriving s m k⟩ := by
  intro h
  change m.dst.2 = rankLast s at h
  change arriving s m k = .troll ∨ promotedKind (arriving s m k) 1 = arriving s m k
  simp only [arriving, if_pos h]
  cases k <;> first | decide | (by_cases hdist : distance m = 1 <;> simp [promotedKind, hdist])

theorem promotion_preserved {p : Position} {m : Move} {k : Kind}
    (ranks : PromotionRanks p) : PromotionRanks (apply p m k) := by
  intro q piece h
  change boardAfter p m k q = some piece at h
  unfold boardAfter at h
  split at h
  next eq =>
    cases eq
    cases h
    exact arriving_allowed _ _ _
  next =>
    split at h
    · contradiction
    · exact ranks q piece h

theorem rights_preserved {p : Position} {m : Move} {k : Kind}
    (rights : JumpRights p) : JumpRights (apply p m k) := by
  intro s h
  change jumpAfter p k s = true at h
  change kingAfter p m k s = home s
  unfold kingAfter jumpAfter at *
  split
  next yes => simp [yes] at h
  next no => exact rights s (by simpa [no] using h)

theorem rights_monotone (p : Position) (m : Move) (k : Kind) (s : Side) :
    (apply p m k).jump s = true → p.jump s = true := by
  change jumpAfter p k s = true → p.jump s = true
  unfold jumpAfter
  split <;> simp

theorem king_consumes_right (p : Position) (m : Move) :
    (apply p m .king).jump p.turn = false := by simp [apply, jumpAfter]

theorem mover_safe {p : Position} {m : Move} {k : Kind} (h : Conditions p m k) :
    PreviousRoyalSafe (apply p m k) := by
  simpa [PreviousRoyalSafe, apply] using h.2.2.2

theorem ep_expires (p : Position) (m : Move) (k : Kind)
    (h : straightDouble p.turn k m = false) : (apply p m k).ep = none := by
  simp [apply, nextEP, h]

theorem ep_double (p : Position) (m : Move) (k : Kind)
    (h : straightDouble p.turn k m = true) :
    (apply p m k).ep = shift m.src 0 p.turn.forward := by
  simp [apply, nextEP, h]

theorem fullmove_positive {p : Position} (m : Move) (k : Kind)
    (h : 0 < p.fullmove) : 0 < (apply p m k).fullmove := by
  simp only [apply]
  split <;> omega

theorem shift_vertical (s q : Square) (delta : Int) :
    shift s 0 delta = some q ↔ q.1 = s.1 ∧ (q.2.val : Int) = (s.2.val : Int) + delta := by
  have file : 0 ≤ (s.1.val : Int) ∧ (s.1.val : Int) < 16 := by
    have h := s.1.isLt
    omega
  have rank := q.2.isLt
  unfold shift
  simp only [Int.add_zero, dif_pos file]
  split
  next onBoard =>
    constructor
    · intro h
      have he := Option.some.inj h
      have h1 := congrArg Prod.fst he
      have h2 := congrArg (fun t : Square => t.2.val) he
      exact ⟨h1.symm, by dsimp at h2; omega⟩
    · rintro ⟨hx, hy⟩
      apply congrArg some
      apply Prod.ext <;> apply Fin.ext
      · exact congrArg Fin.val hx.symm
      · dsimp
        omega
  next offBoard =>
    simp only [reduceCtorEq, false_iff, not_and]
    intro _ hy
    exact offBoard (by omega)

theorem ep_has_pawn {p : Position} {m : Move} {k : Kind}
    (h : epCapture p m k = true) : k = .pawn := by
  simp [epCapture] at h
  exact h.1.1.1.1

theorem ep_clears_victim {p : Position} {m : Move} {k : Kind}
    (h : epCapture p m k = true) : (apply p m k).board (victimSquare m) = none := by
  have hy : dy m = p.turn.forward := by
    simp [epCapture, diagonalForward] at h
    exact h.1.2.2
  have different : victimSquare m ≠ m.dst := by
    intro he
    have e := congrArg (fun q : Square => q.2.val) he
    change m.src.2.val = m.dst.2.val at e
    cases ht : p.turn <;> simp [ht, Side.forward, dy, e] at hy
  simp [apply, boardAfter, different, takenAt, h]

theorem ep_ordinary_disjoint {p : Position} {m : Move} {k : Kind}
    (h : epCapture p m k = true) :
    geometry p.board p.turn k m (p.board m.dst).isSome = false := by
  have pawn := ep_has_pawn h
  simp [epCapture, diagonalForward] at h
  have nonzero : dx m ≠ 0 := by intro e; simp [e] at h
  simp [pawn, geometry, h.1.1.2, nonzero]

theorem jump_ordinary_disjoint {p : Position} {m : Move}
    (h : jumpMove p m = true) :
    geometry p.board p.turn .king m (p.board m.dst).isSome = false := by
  simp [jumpMove] at h
  simp [geometry, h.1.1.1.2]

theorem ep_jump_disjoint {p : Position} {m : Move} {k : Kind}
    (h : epCapture p m k = true) : ¬(k = .king ∧ jumpMove p m = true) := by
  rw [ep_has_pawn h]
  simp

theorem ep_preserved {p : Position} {m : Move} {k : Kind}
    (rules : Conditions p m k) : EPValid (apply p m k) := by
  intro e next
  change nextEP p m k = some e at next
  unfold nextEP at next
  split at next
  next doubled =>
    have fne : p.turn.forward ≠ 0 := by cases p.turn <;> decide
    have direction : p.turn.other.forward = -p.turn.forward := by cases p.turn <;> decide
    obtain ⟨sameFile, crossRank⟩ := (shift_vertical m.src e _).mp next
    have geom : (k = .pawn ∨ k = .prince) ∧ dx m = 0 ∧ dy m = 2 * p.turn.forward := by
      simpa [straightDouble, and_assoc] using doubled
    have hFile : m.dst.1 = m.src.1 := by
      apply Fin.ext
      have h := geom.2.1
      unfold dx at h
      omega
    have dr : (m.dst.2.val : Int) = (m.src.2.val : Int) + 2 * p.turn.forward := by
      have h := geom.2.2
      unfold dy at h
      omega
    have origin : shift e 0 p.turn.other.forward = some m.src :=
      (shift_vertical _ _ _).mpr ⟨sameFile.symm, by rw [direction]; omega⟩
    have dest : shift e 0 (-p.turn.other.forward) = some m.dst :=
      (shift_vertical _ _ _).mpr ⟨hFile.trans sameFile.symm, by rw [direction]; omega⟩
    have srcNe : m.src ≠ m.dst := rules.1
    have eSrc : e ≠ m.src := by
      intro h
      rw [h] at crossRank
      omega
    have eDst : e ≠ m.dst := by
      intro h
      rw [h] at crossRank
      omega
    have noEP : epCapture p m k = false := by
      unfold epCapture diagonalForward
      simp [geom.2.1]
    have landingKind : victimKind p.turn m.dst (arriving p.turn m k) := by
      rcases geom.1 with h | h <;>
        by_cases last : m.dst.2 = rankLast p.turn <;> simp [h, victimKind, arriving, last, promotedKind]
    have ordinary : geometry p.board p.turn k m (p.board m.dst).isSome = true := by
      rcases rules.2.2.1 with h | h | h
      · exact h
      · simp [noEP] at h
      · rcases geom.1 with eq | eq <;> simp [eq] at h
    have notOne : distance m ≠ 1 := by
      have h := geom.2.2
      unfold distance
      cases ht : p.turn <;> simp [ht, Side.forward] at h <;> simp [h, geom.2.1]
    have differentAdvance : 2 * p.turn.forward ≠ p.turn.forward := by omega
    have notStep : dy m ≠ p.turn.forward := by rw [geom.2.2]; omega
    have clear : p.board e = none := by
      rcases geom.1 with h | h <;>
        cases occupied : p.board m.dst <;>
        simp [geometry, h, geom.2.1, geom.2.2, notStep, differentAdvance, notOne, next, occupied,
              diagonalForward] at ordinary
      all_goals exact ordinary
    refine ⟨m.src, m.dst, origin, dest, ?_, ?_, ?_⟩
    · simp [apply, boardAfter, srcNe]
    · simp [apply, boardAfter, eSrc, eDst, takenAt, noEP, clear]
    · simp [apply, boardAfter, isVictim, landingKind]
  next => contradiction

structure Valid (p : Position) : Prop where
  kings : Kings p
  ranks : PromotionRanks p
  rights : JumpRights p
  ep : EPValid p
  safe : PreviousRoyalSafe p
  full : 0 < p.fullmove

theorem valid_step {p q : Position} {m : Move} (valid : Valid p) (h : step p m = some q) :
    Valid q := by
  have legal := (step_exists_iff p m).mp ⟨q, h⟩
  have ok := (accepts_iff p m).mpr legal
  obtain ⟨k, hk, rules⟩ := legal
  have equal : apply p m k = q := by simpa [step, ok, hk] using h
  rw [← equal]
  exact ⟨kings_preserved valid.kings hk rules, promotion_preserved valid.ranks,
         rights_preserved valid.rights, ep_preserved rules, mover_safe rules,
         fullmove_positive m k valid.full⟩

theorem step_unique {p q r : Position} {m : Move}
    (hq : step p m = some q) (hr : step p m = some r) : q = r :=
  Option.some.inj (hq.symm.trans hr)

theorem pawn_advance {p : Position} {m : Move} (rules : Conditions p m .pawn) :
    dy m = p.turn.forward ∨ dy m = 2 * p.turn.forward := by
  rcases rules.2.2.1 with ordinary | ep | jump
  · cases atDest : p.board m.dst <;>
      simp [geometry, diagonalForward, atDest] at ordinary
    · rcases ordinary with h | h
      · exact Or.inl h.2
      · exact Or.inr h.1.2
    · exact Or.inl ordinary.2
  · simp [epCapture, diagonalForward] at ep
    exact Or.inl ep.1.2.2
  · simp at jump

theorem arriving_pawn_origin {s : Side} {m : Move} {k : Kind}
    (h : arriving s m k = .pawn) : k = .pawn := by
  unfold arriving at h
  split at h
  · cases k <;> simp [promotedKind] at h
    split at h <;> contradiction
  · exact h

-- A Pawn can originate in the starting ranks or move further forward.
def PawnBounds (p : Position) : Prop :=
  ∀ s q, p.board q = some ⟨s, .pawn⟩ →
    if s = .white then 3 ≤ q.2.val else q.2.val ≤ 12

theorem pawn_bounds_preserved {p : Position} {m : Move} {k : Kind}
    (bounds : PawnBounds p) (source : p.board m.src = some ⟨p.turn, k⟩)
    (rules : Conditions p m k) : PawnBounds (apply p m k) := by
  intro s q h
  change boardAfter p m k q = some ⟨s, .pawn⟩ at h
  unfold boardAfter at h
  split at h
  next eq =>
    simp only [Option.some.injEq, Piece.mk.injEq] at h
    obtain ⟨rfl, arrived⟩ := h
    have pawn := arriving_pawn_origin arrived
    subst k
    have progress := pawn_advance rules
    have old := bounds p.turn m.src source
    rw [eq]
    cases ht : p.turn <;> simp [ht, Side.forward, dy] at progress old ⊢ <;> omega
  next =>
    split at h
    · contradiction
    · exact bounds s q h

theorem no_promoted_ep_victim {p : Position} {m : Move} {k : Kind}
    (bounds : PawnBounds p) (source : p.board m.src = some ⟨p.turn, k⟩)
    (capture : epCapture p m k = true) :
    (victimSquare m).2 ≠ rankLast p.turn.other := by
  have pawn := ep_has_pawn capture
  subst k
  have h := bounds p.turn m.src source
  intro rank
  have rank := congrArg Fin.val rank
  cases ht : p.turn <;> simp [ht, victimSquare, rankLast, Side.other] at h rank <;> omega

instance (q : Square) (p : Piece) : Decidable (allowed q p) := by
  unfold allowed
  infer_instance

set_option maxRecDepth 8192 in
theorem initial_kings : Kings initial := by
  intro side q
  have white : squares.all (fun r =>
      decide (initial.board r = some ⟨.white, .king⟩ ↔ r = initial.king .white)) = true := by decide
  have black : squares.all (fun r =>
      decide (initial.board r = some ⟨.black, .king⟩ ↔ r = initial.king .black)) = true := by decide
  cases side
  · exact of_decide_eq_true (List.all_eq_true.mp white q (square_mem q))
  · exact of_decide_eq_true (List.all_eq_true.mp black q (square_mem q))

set_option maxRecDepth 8192 in
theorem initial_ranks : PromotionRanks initial := by
  intro q piece atPiece
  have all : squares.all (fun r => match initial.board r with
      | none => true
      | some p => decide (allowed r p)) = true := by decide
  have h := List.all_eq_true.mp all q (square_mem q)
  simpa [atPiece] using h

set_option maxRecDepth 8192 in
theorem initial_valid : Valid initial := by
  refine ⟨initial_kings, initial_ranks, ?_, ?_, ?_, ?_⟩
  · intro s _; rfl
  · intro e h; contradiction
  · unfold PreviousRoyalSafe; decide
  · decide

set_option maxRecDepth 8192 in
theorem initial_pawn_bounds : PawnBounds initial := by
  intro side q atPawn
  have check : squares.all (fun r => match initial.board r with
      | some ⟨s, .pawn⟩ => decide (if s = .white then 3 ≤ r.2.val else r.2.val ≤ 12)
      | _ => true) = true := by decide
  have h := List.all_eq_true.mp check q (square_mem q)
  simpa [atPawn] using h

inductive Reachable : Position → Prop where
  | initial : Reachable initial
  | next : Reachable p → step p m = some q → Reachable q

theorem reachable_valid {p : Position} (path : Reachable p) : Valid p := by
  induction path with
  | initial => exact initial_valid
  | next _ legal valid => exact valid_step valid legal

theorem reachable_pawn_bounds {p : Position} (path : Reachable p) : PawnBounds p := by
  induction path with
  | initial => exact initial_pawn_bounds
  | @next p m q _ stepped ih =>
    have legal := (step_exists_iff p m).mp ⟨q, stepped⟩
    have ok := (accepts_iff p m).mpr legal
    obtain ⟨k, hk, rules⟩ := legal
    have eq : apply p m k = q := by simpa [step, ok, hk] using stepped
    rw [← eq]
    exact pawn_bounds_preserved ih hk rules

inductive Ending where
  | playing | mate (winner : Side) | stalemate | repetition | moveCount | bareKings
  deriving DecidableEq, Repr

structure Key where
  pieces : List (Option Piece)
  turn : Side
  whiteJump : Bool
  blackJump : Bool
  ep : Option Square
  deriving DecidableEq

def repetitionKey (p : Position) : Key :=
  let effective := (legalMoves p).any fun m => epCapture p m .pawn &&
    p.board m.src == some ⟨p.turn, .pawn⟩
  ⟨squares.map p.board, p.turn, p.jump .white, p.jump .black, if effective then p.ep else none⟩

structure Game where
  position : Position
  history : List Key

def start (p : Position) : Game := ⟨p, [repetitionKey p]⟩

def halfmoveLimit : Nat := 200

def ending (g : Game) : Ending :=
  let p := g.position
  if (legalMoves p).isEmpty then
    if inCheck p then .mate p.turn.other else .stalemate
  else if squares.countP (fun q => (p.board q).isSome) = 2 then .bareKings
  else if g.history.count (repetitionKey p) ≥ 3 then .repetition
  else if p.halfmove ≥ halfmoveLimit then .moveCount
  else .playing

def play (g : Game) (m : Move) : Option Game :=
  if ending g = .playing then
    (step g.position m).map fun p => ⟨p, repetitionKey p :: g.history⟩
  else none

theorem mate_precedence (g : Game) (h : (legalMoves g.position).isEmpty = true)
    (c : inCheck g.position = true) : ending g = .mate g.position.turn.other := by
  simp [ending, h, c]

theorem stalemate_precedence (g : Game) (h : (legalMoves g.position).isEmpty = true)
    (c : inCheck g.position = false) : ending g = .stalemate := by
  simp [ending, h, c]

theorem move_count_iff (g : Game) (moves : (legalMoves g.position).isEmpty = false)
    (pieces : squares.countP (fun q => (g.position.board q).isSome) ≠ 2)
    (occurrences : g.history.count (repetitionKey g.position) < 3) :
    ending g = .moveCount ↔ 200 ≤ g.position.halfmove := by
  have notRepeated : ¬ g.history.count (repetitionKey g.position) ≥ 3 := by omega
  simp [ending, moves, pieces, notRepeated, halfmoveLimit]

theorem terminal_no_play (g : Game) (m : Move) (h : ending g ≠ .playing) :
    play g m = none := by simp [play, h]

theorem play_iff (g : Game) (m : Move) :
    (∃ h, play g m = some h) ↔ ending g = .playing ∧ Legal g.position m := by
  unfold play
  by_cases active : ending g = .playing
  · simp only [if_pos active, true_and, active]
    constructor
    · rintro ⟨h, hp⟩
      cases stepEq : step g.position m with
      | none => simp [stepEq] at hp
      | some p => exact (step_exists_iff g.position m).mp ⟨p, stepEq⟩
    · intro legal
      obtain ⟨p, hp⟩ := (step_exists_iff g.position m).mpr legal
      exact ⟨⟨p, repetitionKey p :: g.history⟩, by simp [hp]⟩
  · simp [active]

theorem play_history {g h : Game} {m : Move} (played : play g m = some h) :
    h.history = repetitionKey h.position :: g.history := by
  unfold play at played
  split at played
  · cases next : step g.position m with
    | none => simp [next] at played
    | some p => simp [next] at played; rw [← played]
  · contradiction


end Terachess
