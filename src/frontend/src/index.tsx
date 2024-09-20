import React from "react";
import ReactDOM from "react-dom/client";
import { createHashRouter, RouterProvider } from "react-router-dom";
import { initializeIcons } from "@fluentui/react";
import { AppStateProvider } from './AppStateContext/AppStateContext'; 

import "./index.css";

import Layout from "./pages/layout/Layout";
import Chat from "./pages/chat/Chat";

var chat = <Chat />;

initializeIcons();

const router = createHashRouter([
    {
        path: "/",
        element: (
            <AppStateProvider>
                <Layout />
            </AppStateProvider>
        ),
        children: [
            {
                index: true,
                element: chat
            },
            {
                path: "*",
                lazy: () => import("./pages/NoPage")
            }
        ]
    }
]);

ReactDOM.createRoot(document.getElementById("root") as HTMLElement).render(
    <React.StrictMode>
        <RouterProvider router={router} />
    </React.StrictMode>
);
