// Monkey Balls: the four monkeys of Super Monkey Ball (GameCube) as balls on the Customize page, through Cosmetic Kit
// (a dependency: see info.toml). Each is a clear glass ball (no image) with a tinted lower half and a monkey inside
// (a model): he stays upright, turns to where the ball is going and runs, faster the faster the ball rolls.

import bool AddBall(const string &in, const string &in, const string &in, const string &in, const string &in) from "cosmetic-kit";

void Main()
{
    string f = Plugins::Folder();
    AddBall("monkey-balls.aiai", "AiAi", "", f + "aiai_preview.png", f + "models/aiai.txt");
    AddBall("monkey-balls.meemee", "MeeMee", "", f + "meemee_preview.png", f + "models/meemee.txt");
    AddBall("monkey-balls.baby", "Baby", "", f + "baby_preview.png", f + "models/baby.txt");
    AddBall("monkey-balls.gongon", "GonGon", "", f + "gongon_preview.png", f + "models/gongon.txt");
}
