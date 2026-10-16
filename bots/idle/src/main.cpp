// Idle opponent: drafts a fixed team and never acts. Used to measure pure farming speed (rounds to 1000 gems).
#include <cambc.h>
#include <algorithm>

int main()
{
	using D = cambc::champion_draft;
	while (true)
	{
		try
		{
			if (cambc::is_draft())
			{
				const auto mine = cambc::draft::current_draft(cambc::team::ally);
				for (auto c : { D::willow, D::prism, D::marcella, D::ryth, D::ren })
					if (std::find(mine.begin(), mine.end(), c) == mine.end())
					{
						cambc::draft::pick(c);
						break;
					}
			}
		}
		catch (...)
		{
		}
		cambc::end_turn();
	}
}
