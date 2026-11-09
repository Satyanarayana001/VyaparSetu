import { lazy, Suspense } from "react";
import { Navigate, Route, Routes } from "react-router-dom";
import { DeskLayout, RetailerLayout } from "./components/Layouts";
import { Spinner } from "./components/ui";
import { useAuth } from "./lib/auth";
import type { Role } from "./types";
import Login from "./pages/Login";

const Home = lazy(() => import("./pages/Home"));
const Shop = lazy(() => import("./pages/Shop"));
const Cart = lazy(() => import("./pages/Cart"));
const Message = lazy(() => import("./pages/Message"));
const Orders = lazy(() => import("./pages/Orders"));
const OrderDetail = lazy(() => import("./pages/OrderDetail"));
const DeskOrders = lazy(() => import("./pages/DeskOrders"));
const DeskExport = lazy(() => import("./pages/DeskExport"));
const DeskAliases = lazy(() => import("./pages/DeskAliases"));

function Guard({ role, children }: { role: Role; children: JSX.Element }) {
  const { user, loading } = useAuth();
  if (loading) return <Spinner />;
  if (!user) return <Navigate to="/login" replace />;
  if (user.role !== role) return <Navigate to={user.role === "desk" ? "/desk" : "/"} replace />;
  return children;
}

function SalesmanNote() {
  const { logout } = useAuth();
  return (
    <div className="mx-auto max-w-md p-8 text-center">
      <p className="text-lg font-semibold">Salesman access</p>
      <p className="mt-2 text-muted">The salesman screens are not part of this build. The salesman API is available for authorised retailers only.</p>
      <button className="btn btn-secondary mt-4" onClick={logout}>Sign out</button>
    </div>
  );
}

export default function App() {
  const { user } = useAuth();
  return (
    <Suspense fallback={<Spinner />}>
      <Routes>
        <Route path="/login" element={user ? <Navigate to={user.role === "desk" ? "/desk" : "/"} replace /> : <Login />} />
        <Route element={user?.role === "salesman" ? <SalesmanNote /> : <Guard role="retailer"><RetailerLayout /></Guard>}>
          <Route path="/" element={<Home />} />
          <Route path="/shop" element={<Shop />} />
          <Route path="/cart" element={<Cart />} />
          <Route path="/message" element={<Message />} />
          <Route path="/orders" element={<Orders />} />
          <Route path="/orders/:id" element={<OrderDetail />} />
        </Route>
        <Route element={<Guard role="desk"><DeskLayout /></Guard>}>
          <Route path="/desk" element={<DeskOrders />} />
          <Route path="/desk/orders/:id" element={<DeskOrders />} />
          <Route path="/desk/export" element={<DeskExport />} />
          <Route path="/desk/aliases" element={<DeskAliases />} />
        </Route>
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Suspense>
  );
}
