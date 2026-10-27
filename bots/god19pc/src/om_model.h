// Opponent-model window classifier (P.opp_model): multinomial logistic regression fitted by tools/omfit.py on labelled
// sparring traces (traces_train_v1.jsonl, forgetting 0.8); logit_k = W[k] . features + B[k], features as OppModel::features().
#pragma once

constexpr int OM_NF = 17;
constexpr int OM_NC = 2;
constexpr int OM_NROW = 1; // 1 = binary: the row is the logit of the second class against the first
// classes, in order: none, raider
constexpr int OM_CLASS_ARC[OM_NC] = { 0, 2 };
constexpr float OM_W[OM_NROW][OM_NF] = {
	{ 1.021797e+00f, -1.512124e+00f, -3.037576e+00f, 4.380006e-01f, 4.638108e+00f, 4.245583e+00f, -4.512338e+00f, -1.780040e+00f, -1.781146e+01f, 1.656866e+01f, 1.388535e+00f, 2.301178e-01f, -2.750989e+00f, -4.550399e-01f, -1.093178e+00f, 1.164279e+00f, 2.229799e+01f },
};
constexpr float OM_B[OM_NROW] = { 4.310091e-01f };
