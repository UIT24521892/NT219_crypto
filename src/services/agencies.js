import api from "./api";

export async function listAgencies() {
  const res = await api.get("/agencies");
  return res.data;
}

export async function assignAgency(userEmail, agencyCode) {
  const res = await api.put("/agencies/assign", {
    user_email: userEmail,
    agency_code: agencyCode || null,
  });
  return res.data;
}
