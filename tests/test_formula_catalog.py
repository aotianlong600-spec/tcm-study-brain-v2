from pathlib import Path
import json
import unittest

from fastapi.testclient import TestClient

from app.main import app


ROOT = Path(__file__).resolve().parents[1]


class FormulaCatalogTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def test_overview_is_local_and_bounded(self):
        data = self.client.get("/api/overview").json()
        self.assertEqual(data["formulas"], 299)
        self.assertEqual(data["herbs"], 351)
        self.assertEqual(data["by_book"], {"伤寒论": 113, "金匮要略": 186})
        self.assertEqual(data["source_pending"], 1)
        self.assertEqual(data["modules"]["acupuncture"], "not_imported")

    def test_formula_detail_keeps_dose_and_source(self):
        data = self.client.get("/api/formulas/shanghan%3A%E6%A1%82%E6%9E%9D%E6%B1%A4").json()
        self.assertEqual(data["name"], "桂枝汤")
        self.assertEqual(data["expected_count"], 5)
        self.assertEqual(data["source"]["line"], 295)
        self.assertTrue(all(row["dose"] for row in data["ingredients"]))
        self.assertEqual(data["evidence"]["review_level"], "完整")
        self.assertEqual(data["evidence"]["six_channel"]["name"], "太阳病")
        self.assertGreaterEqual(len(data["evidence"]["six_channel"]["original"]), 3)
        self.assertGreaterEqual(len(data["evidence"]["usage_modern"]["steps"]), 5)
        self.assertGreaterEqual(len(data["evidence"]["symptoms"]), 8)
        self.assertGreaterEqual(len(data["evidence"]["page_reading"]), 5)
        self.assertGreaterEqual(len(data["evidence"]["overview"]["paragraphs"]), 4)

    def test_formula_to_herb_link(self):
        data = self.client.get("/api/formulas/shanghan%3A%E6%A1%82%E6%9E%9D%E6%B1%A4").json()
        self.assertTrue(any(row.get("herb_id") == "bencao:牡桂" for row in data["ingredients"]))
        self.assertEqual(data["evidence"]["review_status"], "reviewed")
        self.assertIn("有汗、恶风", data["evidence"]["why"])

    def test_gegen_formula_preserves_variant_source(self):
        data = self.client.get("/api/formulas/shanghan%3A%E6%A1%82%E6%9E%9D%E5%8A%A0%E8%91%9B%E6%A0%B9%E6%B1%A4").json()
        self.assertEqual(data["name"], "桂枝加葛根汤")
        self.assertEqual(data["evidence"]["review_level"], "完整")
        self.assertEqual(
            [(row["name"], row["dose"], row.get("processing")) for row in data["ingredients"]],
            [
                (row["name"], row["dose"], row.get("processing"))
                for row in data["source_ingredients"]
                if row["name"] != "麻黄"
            ],
        )
        self.assertEqual(data["source_expected_count"], 7)
        self.assertIn("不须啜粥", data["evidence"]["usage_original"]["text"])
        self.assertIn("麻黄", data["evidence"]["formula_original"]["text"])
        self.assertIn("葛根四两", data["evidence"]["page_reading"][1]["text"])
        self.assertEqual(data["evidence"]["usage_modern"]["source_pages"], [18])

    def test_guizhi_fuzi_formula_is_fully_reviewed(self):
        data = self.client.get("/api/formulas/shanghan%3A%E6%A1%82%E6%9E%9D%E5%8A%A0%E9%99%84%E5%AD%90%E6%B1%A4").json()
        evidence = data["evidence"]
        self.assertEqual(data["name"], "桂枝加附子汤")
        self.assertEqual(evidence["review_level"], "完整")
        self.assertEqual(evidence["six_channel"]["name"], "太阳病")
        self.assertIn("汗漏不止", evidence["overview"]["title"] + "".join(evidence["overview"]["paragraphs"]))
        self.assertIn("恶风", [row["name"] for row in evidence["symptoms"]])
        self.assertIn("小便难", [row["name"] for row in evidence["symptoms"]])
        self.assertIn("四肢微急", [row["name"] for row in evidence["symptoms"]])
        self.assertIn("附子一枚，炮，去皮，破八片", evidence["formula_original"]["text"])
        self.assertIn("以水七升", evidence["usage_original"]["text"])
        self.assertIn("以水六升", evidence["usage_modern"]["source_text"])
        self.assertIn("一服汗止，停后服", evidence["usage_modern"]["source_text"])
        self.assertIn("七升", evidence["proofreading"][1]["note"])
        self.assertIn("六升", evidence["proofreading"][1]["note"])

    def test_guizhi_qu_shaoyao_formula_is_fully_reviewed(self):
        data = self.client.get("/api/formulas/shanghan%3A%E6%A1%82%E6%9E%9D%E5%8E%BB%E8%8A%8D%E8%8D%AF%E6%B1%A4").json()
        evidence = data["evidence"]
        self.assertEqual(data["name"], "桂枝去芍药汤")
        self.assertEqual(evidence["review_level"], "完整")
        self.assertEqual(evidence["six_channel"]["name"], "太阳病")
        names = [row["name"] for row in evidence["symptoms"]]
        self.assertIn("脉促", names)
        self.assertIn("胸满", names)
        self.assertIn("桂枝（三两去皮）", evidence["formula_original"]["text"])
        self.assertIn("芍药", evidence["rationale"]["full_text"])
        self.assertIn("以水七升", evidence["usage_original"]["text"])
        self.assertEqual(evidence["page_reading"][0]["page"], 21)
        self.assertEqual(evidence["page_reading"][1]["page"], 22)
        self.assertIn("胸满", evidence["rationale"]["full_text"])

    def test_guizhi_qu_shaoyao_jia_fuzi_formula_is_fully_reviewed(self):
        data = self.client.get("/api/formulas/shanghan%3A%E6%A1%82%E6%9E%9D%E5%8E%BB%E8%8A%8D%E8%8D%AF%E5%8A%A0%E9%99%84%E5%AD%90%E6%B1%A4").json()
        evidence = data["evidence"]
        self.assertEqual(data["name"], "桂枝去芍药加附子汤")
        self.assertEqual(evidence["review_level"], "完整")
        self.assertEqual(evidence["six_channel"]["name"], "太阳病")
        names = [row["name"] for row in evidence["symptoms"]]
        self.assertIn("微恶寒", names)
        self.assertIn("胸满", names)
        self.assertIn("附子（一枚。炮。去皮。破八片。）", evidence["formula_original"]["text"])
        self.assertIn("以水七升", evidence["usage_original"]["text"])
        self.assertIn("一服恶寒止，停后服", evidence["usage_modern"]["source_text"])
        self.assertEqual(evidence["page_reading"][0]["page"], 21)
        self.assertEqual(evidence["page_reading"][1]["page"], 22)
        self.assertIn("附子", evidence["rationale"]["full_text"])

    def test_guizhi_mahuang_geban_formula_is_fully_reviewed(self):
        data = self.client.get("/api/formulas/shanghan%3A%E6%A1%82%E6%9E%9D%E9%BA%BB%E9%BB%84%E5%90%84%E5%8D%8A%E6%B1%A4").json()
        evidence = data["evidence"]
        self.assertEqual(data["name"], "桂枝麻黄各半汤")
        self.assertEqual(evidence["review_level"], "完整")
        names = [row["name"] for row in evidence["symptoms"]]
        self.assertIn("如疟状", names)
        self.assertIn("热多寒少", names)
        self.assertIn("身痒", names)
        self.assertIn("桂枝一两十六铢", evidence["formula_original"]["text"])
        self.assertIn("先煮麻黄一二沸", evidence["usage_original"]["text"])
        self.assertIn("温服六合", evidence["usage_original"]["text"])
        self.assertEqual(evidence["page_reading"][0]["page"], 22)
        self.assertEqual(evidence["page_reading"][1]["page"], 23)
        self.assertIn("桂枝二麻黄一汤", evidence["rationale"]["full_text"])

    def test_guizhi_er_mahuang_yi_formula_is_fully_reviewed(self):
        data = self.client.get("/api/formulas/shanghan%3A%E6%A1%82%E6%9E%9D%E4%BA%8C%E9%BA%BB%E9%BB%84%E4%B8%80%E6%B1%A4").json()
        evidence = data["evidence"]
        self.assertEqual(data["name"], "桂枝二麻黄一汤")
        self.assertEqual(evidence["review_level"], "完整")
        names = [row["name"] for row in evidence["symptoms"]]
        self.assertIn("大汗出", names)
        self.assertIn("脉洪大", names)
        self.assertIn("形似疟", names)
        self.assertIn("一日再发", names)
        self.assertIn("桂枝一两十七铢", evidence["formula_original"]["text"])
        self.assertIn("杏仁十六个", evidence["formula_original"]["text"])
        self.assertIn("麻黄十六铢", evidence["formula_original"]["text"])
        self.assertIn("先煮麻黄一二沸", evidence["usage_original"]["text"])
        self.assertEqual(evidence["page_reading"][0]["page"], 24)
        self.assertIn("二十六个", evidence["proofreading"][1]["note"])
        self.assertIn("十六个", evidence["proofreading"][1]["note"])

    def test_baihu_jia_renshen_formula_is_fully_reviewed(self):
        data = self.client.get("/api/formulas/shanghan%3A%E7%99%BD%E8%99%8E%E5%8A%A0%E4%BA%BA%E5%8F%82%E6%B1%A4").json()
        evidence = data["evidence"]
        self.assertEqual(data["name"], "白虎加人参汤")
        self.assertEqual(evidence["review_level"], "完整")
        self.assertEqual(evidence["six_channel"]["name"], "阳明病")
        names = [row["name"] for row in evidence["symptoms"]]
        self.assertIn("大汗出", names)
        self.assertIn("大烦渴不解", names)
        self.assertIn("脉洪大", names)
        self.assertIn("知母六两", evidence["formula_original"]["text"])
        self.assertIn("石膏一斤", evidence["formula_original"]["text"])
        self.assertIn("人参三两", evidence["formula_original"]["text"])
        self.assertIn("煮米熟", evidence["usage_original"]["text"])
        self.assertEqual(evidence["page_reading"][0]["page"], 25)
        self.assertEqual(evidence["page_reading"][1]["page"], 26)
        self.assertIn("甘草二两", evidence["proofreading"][0]["note"])
        self.assertIn("甘草三两", evidence["proofreading"][1]["note"])

    def test_guizhi_er_yuebi_yi_formula_is_fully_reviewed(self):
        data = self.client.get("/api/formulas/shanghan%3A%E6%A1%82%E6%9E%9D%E4%BA%8C%E8%B6%8A%E5%A9%A2%E4%B8%80%E6%B1%A4").json()
        evidence = data["evidence"]
        self.assertEqual(data["name"], "桂枝二越婢一汤")
        self.assertEqual(evidence["review_level"], "完整")
        names = [row["name"] for row in evidence["symptoms"]]
        self.assertIn("烦躁", names)
        self.assertIn("发热恶寒", names)
        self.assertIn("热多寒少", names)
        self.assertIn("脉微弱", names)
        self.assertIn("麻黄十八铢", evidence["formula_original"]["text"])
        self.assertIn("石膏二十四铢", evidence["formula_original"]["text"])
        self.assertIn("无阳", evidence["rationale"]["full_text"])
        self.assertIn("石膏", evidence["rationale"]["full_text"])
        self.assertIn("小便", evidence["rationale"]["full_text"])
        self.assertEqual(evidence["page_reading"][0]["page"], 26)
        self.assertEqual(evidence["page_reading"][1]["page"], 27)
        self.assertIn("争议", evidence["proofreading"][1]["note"])

    def test_guizhi_qu_gui_jia_fuling_baizhu_formula_is_fully_reviewed(self):
        data = self.client.get("/api/formulas/shanghan%3A%E6%A1%82%E6%9E%9D%E5%8E%BB%E6%A1%82%E5%8A%A0%E8%8C%AF%E8%8B%93%E7%99%BD%E6%9C%AF%E6%B1%A4").json()
        evidence = data["evidence"]
        self.assertEqual(data["name"], "桂枝去桂加茯苓白术汤")
        self.assertEqual(evidence["review_level"], "完整")
        names = [row["name"] for row in evidence["symptoms"]]
        for name in ("头项强痛", "翕翕发热", "无汗", "心下满微痛", "小便不利"):
            self.assertIn(name, names)
        self.assertIn("芍药三两", evidence["formula_original"]["text"])
        self.assertIn("茯苓三两", evidence["formula_original"]["text"])
        self.assertIn("白术三两", evidence["formula_original"]["text"])
        self.assertIn("小便利则愈", evidence["usage_original"]["text"])
        self.assertEqual(evidence["page_reading"][0]["page"], 27)
        self.assertEqual(evidence["page_reading"][1]["page"], 28)
        self.assertIn("去桂", evidence["rationale"]["full_text"])
        self.assertIn("去芍药", evidence["rationale"]["full_text"])
        self.assertIn("去桂", evidence["proofreading"][1]["note"])
        self.assertIn("去芍药", evidence["proofreading"][1]["note"])

    def test_gancao_ganjiang_formula_is_fully_reviewed(self):
        data = self.client.get("/api/formulas/shanghan%3A%E7%94%98%E8%8D%89%E5%B9%B2%E5%A7%9C%E6%B1%A4").json()
        evidence = data["evidence"]
        self.assertEqual(data["name"], "甘草干姜汤")
        self.assertEqual(evidence["review_level"], "完整")
        names = [row["name"] for row in evidence["symptoms"]]
        self.assertIn("厥", names)
        self.assertIn("咽中干", names)
        self.assertIn("烦躁", names)
        self.assertIn("吐逆", names)
        self.assertIn("甘草四两炙", evidence["formula_original"]["text"])
        self.assertIn("干姜二两", evidence["formula_original"]["text"])
        self.assertIn("以水三升", evidence["usage_original"]["text"])
        self.assertIn("分温再服", evidence["usage_original"]["text"])
        self.assertEqual(evidence["page_reading"][0]["page"], 28)
        self.assertEqual(evidence["page_reading"][1]["page"], 30)
        self.assertIn("复其阳", evidence["rationale"]["full_text"])
        self.assertIn("二比一", evidence["rationale"]["full_text"])
        self.assertIn("甘草四两", evidence["proofreading"][1]["note"])
        self.assertIn("玉函二两", evidence["proofreading"][1]["note"])

    def test_shaoyao_gancao_formula_is_fully_reviewed(self):
        data = self.client.get("/api/formulas/shanghan%3A%E8%8A%8D%E8%8D%AF%E7%94%98%E8%8D%89%E6%B1%A4").json()
        evidence = data["evidence"]
        self.assertEqual(data["name"], "芍药甘草汤")
        self.assertEqual(evidence["review_level"], "完整")
        names = [row["name"] for row in evidence["symptoms"]]
        self.assertIn("脚挛急", names)
        self.assertIn("腹痛", names)
        self.assertIn("白芍药四两", evidence["formula_original"]["text"])
        self.assertIn("甘草四两炙", evidence["formula_original"]["text"])
        self.assertIn("以水三升", evidence["usage_original"]["text"])
        self.assertIn("分温再服", evidence["usage_original"]["text"])
        self.assertEqual(evidence["page_reading"][0]["page"], 28)
        self.assertEqual(evidence["page_reading"][1]["page"], 30)
        self.assertIn("去杖汤", evidence["rationale"]["full_text"])
        self.assertIn("脚挛", evidence["rationale"]["full_text"])
        self.assertIn("白芍药四两", evidence["proofreading"][1]["note"])
        self.assertIn("甘草四两", evidence["proofreading"][1]["note"])

    def test_tiaowei_chengqi_formula_is_fully_reviewed(self):
        data = self.client.get("/api/formulas/shanghan%3A%E8%B0%83%E8%83%83%E6%89%BF%E6%B0%94%E6%B1%A4").json()
        evidence = data["evidence"]
        self.assertEqual(data["name"], "调胃承气汤")
        self.assertEqual(evidence["review_level"], "完整")
        self.assertEqual(evidence["six_channel"]["name"], "阳明病")
        names = [row["name"] for row in evidence["symptoms"]]
        self.assertIn("胃气不和", names)
        self.assertIn("谵语", names)
        self.assertIn("大黄四两", evidence["formula_original"]["text"])
        self.assertIn("甘草二两炙", evidence["formula_original"]["text"])
        self.assertIn("芒硝半升", evidence["formula_original"]["text"])
        self.assertIn("少少温服", evidence["usage_original"]["text"])
        self.assertEqual(evidence["page_reading"][0]["page"], 29)
        self.assertEqual(evidence["page_reading"][1]["page"], 30)
        self.assertIn("调胃", evidence["rationale"]["full_text"])
        self.assertIn("大黄", evidence["rationale"]["full_text"])
        self.assertIn("半升", evidence["proofreading"][1]["note"])
        self.assertIn("半斤", evidence["proofreading"][1]["note"])

    def test_sini_formula_is_fully_reviewed(self):
        data = self.client.get("/api/formulas/shanghan%3A%E5%9B%9B%E9%80%86%E6%B1%A4").json()
        evidence = data["evidence"]
        self.assertEqual(data["name"], "四逆汤")
        self.assertEqual(evidence["review_level"], "完整")
        self.assertEqual(evidence["six_channel"]["id"], "shaoyin")
        names = [row["name"] for row in evidence["symptoms"]]
        self.assertIn("四肢厥逆", names)
        self.assertIn("下利清谷", names)
        self.assertIn("小便清利", names)
        self.assertIn("甘草二两炙", evidence["formula_original"]["text"])
        self.assertIn("干姜一两半", evidence["formula_original"]["text"])
        self.assertIn("附子一枚", evidence["formula_original"]["text"])
        self.assertIn("以水三升", evidence["usage_original"]["text"])
        self.assertIn("强人可大附子一枚", evidence["usage_original"]["text"])
        self.assertEqual(evidence["page_reading"][0]["page"], 29)
        self.assertEqual(evidence["page_reading"][1]["page"], 31)
        self.assertIn("生附子", evidence["rationale"]["full_text"])
        self.assertIn("亡阳", evidence["rationale"]["full_text"])
        self.assertIn("干姜一两半", evidence["proofreading"][1]["note"])
        self.assertIn("生附子一枚", evidence["proofreading"][1]["note"])

    def test_gegen_formula_is_fully_reviewed(self):
        data = self.client.get("/api/formulas/shanghan%3A%E8%91%9B%E6%A0%B9%E6%B1%A4").json()
        evidence = data["evidence"]
        self.assertEqual(data["name"], "葛根汤")
        self.assertEqual(evidence["review_level"], "完整")
        self.assertEqual(evidence["six_channel"]["name"], "太阳病")
        names = [row["name"] for row in evidence["symptoms"]]
        self.assertIn("项背强几几", names)
        self.assertIn("无汗", names)
        self.assertIn("恶风", names)
        self.assertIn("葛根四两", evidence["formula_original"]["text"])
        self.assertIn("麻黄三两", evidence["formula_original"]["text"])
        self.assertIn("先煮麻黄葛根", evidence["usage_original"]["text"])
        self.assertIn("覆取微似汗", evidence["usage_original"]["text"])
        self.assertEqual(evidence["page_reading"][0]["page"], 32)
        self.assertEqual(evidence["page_reading"][1]["page"], 33)
        self.assertIn("桂枝加葛根汤", evidence["rationale"]["full_text"])
        self.assertIn("无汗", evidence["rationale"]["full_text"])
        self.assertIn("外台", evidence["proofreading"][1]["note"])

    def test_gegen_jia_banxia_formula_is_fully_reviewed(self):
        data = self.client.get("/api/formulas/shanghan%3A%E8%91%9B%E6%A0%B9%E5%8A%A0%E5%8D%8A%E5%A4%8F%E6%B1%A4").json()
        evidence = data["evidence"]
        self.assertEqual(data["name"], "葛根加半夏汤")
        self.assertEqual(evidence["review_level"], "完整")
        names = [row["name"] for row in evidence["symptoms"]]
        self.assertIn("不下利", names)
        self.assertIn("呕", names)
        self.assertIn("项背强几几", names)
        self.assertIn("半夏半升", evidence["formula_original"]["text"])
        self.assertIn("生姜二两", evidence["formula_original"]["text"])
        self.assertIn("先煮葛根麻黄", evidence["usage_original"]["text"])
        self.assertEqual(evidence["page_reading"][0]["page"], 34)
        self.assertIn("半夏", evidence["rationale"]["full_text"])
        self.assertIn("生姜", evidence["rationale"]["full_text"])
        self.assertIn("停饮", evidence["rationale"]["full_text"])
        self.assertIn("半夏半升", evidence["proofreading"][1]["note"])
        self.assertIn("生姜二两", evidence["proofreading"][1]["note"])
        self.assertIn("玉函", evidence["proofreading"][1]["note"])

    def test_gegen_huangqin_huanglian_formula_is_fully_reviewed(self):
        data = self.client.get("/api/formulas/shanghan%3A%E8%91%9B%E6%A0%B9%E9%BB%84%E8%8A%A9%E9%BB%84%E8%BF%9E%E6%B1%A4").json()
        evidence = data["evidence"]
        self.assertEqual(data["name"], "葛根黄芩黄连汤")
        self.assertEqual(evidence["review_level"], "完整")
        names = [row["name"] for row in evidence["symptoms"]]
        self.assertIn("下利", names)
        self.assertIn("脉促", names)
        self.assertIn("喘而汗出", names)
        self.assertIn("葛根半斤", evidence["formula_original"]["text"])
        self.assertIn("黄芩三两", evidence["formula_original"]["text"])
        self.assertIn("黄连三两", evidence["formula_original"]["text"])
        self.assertIn("先煮葛根", evidence["usage_original"]["text"])
        self.assertIn("分温再服", evidence["usage_original"]["text"])
        self.assertEqual(evidence["page_reading"][0]["page"], 34)
        self.assertEqual(evidence["page_reading"][1]["page"], 35)
        self.assertIn("热利", evidence["rationale"]["full_text"])
        self.assertIn("表邪", evidence["rationale"]["full_text"])
        self.assertIn("葛根半斤", evidence["proofreading"][1]["note"])
        self.assertIn("黄连三两", evidence["proofreading"][1]["note"])

    def test_mahuang_formula_is_fully_reviewed(self):
        data = self.client.get("/api/formulas/shanghan%3A%E9%BA%BB%E9%BB%84%E6%B1%A4").json()
        evidence = data["evidence"]
        self.assertEqual(data["name"], "麻黄汤")
        self.assertEqual(evidence["review_level"], "完整")
        names = [row["name"] for row in evidence["symptoms"]]
        for name in ("头痛", "发热", "身疼", "腰痛", "骨节疼痛", "恶风", "无汗", "喘"):
            self.assertIn(name, names)
        self.assertIn("麻黄三两", evidence["formula_original"]["text"])
        self.assertIn("桂枝二两", evidence["formula_original"]["text"])
        self.assertIn("甘草一两", evidence["formula_original"]["text"])
        self.assertIn("杏仁七十个", evidence["formula_original"]["text"])
        self.assertIn("先煮麻黄减二升", evidence["usage_original"]["text"])
        self.assertIn("不须啜粥", evidence["usage_original"]["text"])
        self.assertEqual(evidence["page_reading"][0]["page"], 35)
        self.assertEqual(evidence["page_reading"][1]["page"], 36)
        self.assertIn("无汗", evidence["rationale"]["full_text"])
        self.assertIn("杏仁", evidence["rationale"]["full_text"])
        self.assertIn("七十个", evidence["proofreading"][1]["note"])
        self.assertIn("外台", evidence["proofreading"][1]["note"])

    def test_daqinglong_formula_is_fully_reviewed(self):
        data = self.client.get("/api/formulas/shanghan%3A%E5%A4%A7%E9%9D%92%E9%BE%99%E6%B1%A4").json()
        evidence = data["evidence"]
        self.assertEqual(data["name"], "大青龙汤")
        self.assertEqual(evidence["review_level"], "完整")
        names = [row["name"] for row in evidence["symptoms"]]
        for name in ("脉浮紧", "发热恶寒", "身疼痛", "不汗出", "烦躁"):
            self.assertIn(name, names)
        self.assertIn("麻黄六两", evidence["formula_original"]["text"])
        self.assertIn("石膏如鸡子大", evidence["formula_original"]["text"])
        self.assertIn("大枣十枚", evidence["formula_original"]["text"])
        self.assertIn("温粉扑之", evidence["usage_original"]["text"])
        self.assertIn("一服汗者，停后服", evidence["usage_original"]["text"])
        self.assertEqual(evidence["page_reading"][0]["page"], 37)
        self.assertEqual(evidence["page_reading"][1]["page"], 38)
        self.assertIn("表寒里热", evidence["rationale"]["full_text"])
        self.assertIn("脉微弱", evidence["rationale"]["full_text"])
        self.assertIn("石膏", evidence["rationale"]["full_text"])
        self.assertIn("麻黄六两", evidence["proofreading"][1]["note"])
        self.assertIn("石膏如鸡子大", evidence["proofreading"][1]["note"])
        self.assertIn("大枣十枚", evidence["proofreading"][1]["note"])

    def test_xiaoqinglong_formula_is_fully_reviewed(self):
        data = self.client.get("/api/formulas/shanghan%3A%E5%B0%8F%E9%9D%92%E9%BE%99%E6%B1%A4").json()
        evidence = data["evidence"]
        self.assertEqual(data["name"], "小青龙汤")
        self.assertEqual(evidence["review_level"], "完整")
        names = [row["name"] for row in evidence["symptoms"]]
        for name in ("心下有水气", "干呕", "发热而咳", "咳而微喘", "痰白", "不渴"):
            self.assertIn(name, names)
        self.assertIn("麻黄三两", evidence["formula_original"]["text"])
        self.assertIn("细辛三两", evidence["formula_original"]["text"])
        self.assertIn("五味子半升", evidence["formula_original"]["text"])
        self.assertIn("半夏半升", evidence["formula_original"]["text"])
        self.assertIn("先煮麻黄", evidence["usage_original"]["text"])
        self.assertIn("若渴去半夏", evidence["usage_original"]["text"])
        self.assertEqual(evidence["page_reading"][0]["page"], 39)
        self.assertEqual(evidence["page_reading"][1]["page"], 40)
        self.assertIn("表寒里寒", evidence["rationale"]["full_text"])
        self.assertIn("水饮", evidence["rationale"]["full_text"])
        self.assertIn("大青龙", evidence["rationale"]["full_text"])
        self.assertIn("五味子半升", evidence["proofreading"][1]["note"])
        self.assertIn("五味子半斤", evidence["proofreading"][1]["note"])

    def test_guizhi_houpo_xingren_formula_is_fully_reviewed(self):
        data = self.client.get("/api/formulas/shanghan%3A%E6%A1%82%E6%9E%9D%E5%8A%A0%E5%8E%9A%E6%9C%B4%E6%9D%8F%E4%BB%81%E6%B1%A4").json()
        evidence = data["evidence"]
        self.assertEqual(data["name"], "桂枝加厚朴杏仁汤")
        self.assertEqual(evidence["review_level"], "完整")
        names = [row["name"] for row in evidence["symptoms"]]
        self.assertIn("微喘", names)
        self.assertIn("咳嗽", names)
        self.assertIn("表未解", names)
        self.assertIn("厚朴二两", evidence["formula_original"]["text"])
        self.assertIn("杏仁五十枚", evidence["formula_original"]["text"])
        self.assertIn("以水七升", evidence["usage_original"]["text"])
        self.assertIn("覆取微似汗", evidence["usage_original"]["text"])
        self.assertEqual(evidence["page_reading"][0]["page"], 41)
        self.assertIn("厚朴", evidence["rationale"]["full_text"])
        self.assertIn("杏仁", evidence["rationale"]["full_text"])
        self.assertIn("咳嗽", evidence["rationale"]["full_text"])
        self.assertIn("厚朴二两", evidence["proofreading"][1]["note"])
        self.assertIn("杏仁五十枚", evidence["proofreading"][1]["note"])
        self.assertIn("成本", evidence["proofreading"][1]["note"])

    def test_ganjiang_fuzi_formula_is_fully_reviewed(self):
        data = self.client.get("/api/formulas/shanghan%3A%E5%B9%B2%E5%A7%9C%E9%99%84%E5%AD%90%E6%B1%A4").json()
        evidence = data["evidence"]
        self.assertEqual(data["name"], "干姜附子汤")
        self.assertEqual(evidence["review_level"], "完整")
        self.assertEqual(evidence["six_channel"]["id"], "shaoyin")
        names = [row["name"] for row in evidence["symptoms"]]
        for name in ("昼日烦躁不得眠", "夜而安静", "不呕", "不渴", "无表证", "脉沉微", "身无大热"):
            self.assertIn(name, names)
        self.assertIn("干姜一两", evidence["formula_original"]["text"])
        self.assertIn("附子一枚生用去皮切八片", evidence["formula_original"]["text"])
        self.assertIn("以水三升", evidence["usage_original"]["text"])
        self.assertIn("顿服", evidence["usage_original"]["text"])
        self.assertEqual(evidence["page_reading"][0]["page"], 48)
        self.assertEqual(evidence["page_reading"][1]["page"], 49)
        self.assertIn("阳虚", evidence["rationale"]["full_text"])
        self.assertIn("无甘草", evidence["rationale"]["full_text"])
        self.assertIn("四逆汤", evidence["rationale"]["full_text"])
        self.assertIn("干姜一两", evidence["proofreading"][1]["note"])
        self.assertIn("生附子一枚", evidence["proofreading"][1]["note"])

    def test_guizhi_xinjia_formula_is_fully_reviewed(self):
        data = self.client.get("/api/formulas/shanghan%3A%E6%A1%82%E6%9E%9D%E5%8A%A0%E8%8A%8D%E8%8D%AF%E7%94%9F%E5%A7%9C%E4%BA%BA%E5%8F%82%E6%96%B0%E5%8A%A0%E6%B1%A4").json()
        evidence = data["evidence"]
        self.assertEqual(data["name"], "桂枝加芍药生姜人参新加汤")
        self.assertEqual(evidence["review_level"], "完整")
        self.assertEqual(evidence["six_channel"]["name"], "太阳病")
        names = [row["name"] for row in evidence["symptoms"]]
        self.assertIn("身疼痛", names)
        self.assertIn("脉沉迟", names)
        self.assertIn("发汗后", names)
        self.assertIn("芍药四两", evidence["formula_original"]["text"])
        self.assertIn("人参三两", evidence["formula_original"]["text"])
        self.assertIn("生姜四两", evidence["formula_original"]["text"])
        self.assertIn("以水一斗二升", evidence["usage_original"]["text"])
        self.assertIn("分温服", evidence["usage_original"]["text"])
        self.assertEqual(evidence["page_reading"][0]["page"], 49)
        self.assertIn("人参", evidence["rationale"]["full_text"])
        self.assertIn("汗流不止", evidence["rationale"]["full_text"])
        self.assertIn("桂枝加附子汤", evidence["rationale"]["full_text"])
        self.assertIn("芍药四两", evidence["proofreading"][1]["note"])
        self.assertIn("生姜四两", evidence["proofreading"][1]["note"])
        self.assertIn("人参三两", evidence["proofreading"][1]["note"])

    def test_mahuang_xingren_gancao_shigao_formula_is_fully_reviewed(self):
        data = self.client.get("/api/formulas/shanghan%3A%E9%BA%BB%E9%BB%84%E6%9D%8F%E4%BB%81%E7%94%98%E8%8D%89%E7%9F%B3%E8%86%8F%E6%B1%A4").json()
        evidence = data["evidence"]
        self.assertEqual(data["name"], "麻黄杏仁甘草石膏汤")
        self.assertEqual(evidence["review_level"], "完整")
        names = [row["name"] for row in evidence["symptoms"]]
        self.assertIn("汗出而喘", names)
        self.assertIn("无大热", names)
        self.assertIn("肺热", names)
        self.assertIn("麻黄四两", evidence["formula_original"]["text"])
        self.assertIn("杏仁五十个", evidence["formula_original"]["text"])
        self.assertIn("石膏半斤", evidence["formula_original"]["text"])
        self.assertIn("先煮麻黄减二升", evidence["usage_original"]["text"])
        self.assertIn("以水七升", evidence["usage_original"]["text"])
        self.assertEqual(evidence["page_reading"][0]["page"], 50)
        self.assertIn("肺热", evidence["rationale"]["full_text"])
        self.assertIn("汗出", evidence["rationale"]["full_text"])
        self.assertIn("石膏", evidence["rationale"]["full_text"])
        self.assertIn("麻黄四两", evidence["proofreading"][1]["note"])
        self.assertIn("石膏半斤", evidence["proofreading"][1]["note"])
        self.assertIn("杏仁五十个", evidence["proofreading"][1]["note"])

    def test_guizhi_gancao_formula_is_fully_reviewed(self):
        data = self.client.get("/api/formulas/shanghan%3A%E6%A1%82%E6%9E%9D%E7%94%98%E8%8D%89%E6%B1%A4").json()
        evidence = data["evidence"]
        self.assertEqual(data["name"], "桂枝甘草汤")
        self.assertEqual(evidence["review_level"], "完整")
        names = [row["name"] for row in evidence["symptoms"]]
        for name in ("发汗过多", "叉手自冒心", "心下悸", "欲得按"):
            self.assertIn(name, names)
        self.assertIn("桂枝四两", evidence["formula_original"]["text"])
        self.assertIn("甘草二两炙", evidence["formula_original"]["text"])
        self.assertIn("以水三升", evidence["usage_original"]["text"])
        self.assertIn("顿服", evidence["usage_original"]["text"])
        self.assertEqual(evidence["page_reading"][0]["page"], 51)
        self.assertIn("桂枝", evidence["rationale"]["full_text"])
        self.assertIn("甘草", evidence["rationale"]["full_text"])
        self.assertIn("心下悸", evidence["rationale"]["full_text"])
        self.assertIn("不用芍药", evidence["rationale"]["full_text"])
        self.assertIn("桂枝四两", evidence["proofreading"][1]["note"])
        self.assertIn("甘草二两", evidence["proofreading"][1]["note"])

    def test_fuling_guizhi_gancao_dazao_formula_is_fully_reviewed(self):
        data = self.client.get("/api/formulas/shanghan%3A%E8%8C%AF%E8%8B%93%E6%A1%82%E6%9E%9D%E7%94%98%E8%8D%89%E5%A4%A7%E6%9E%A3%E6%B1%A4").json()
        evidence = data["evidence"]
        self.assertEqual(data["name"], "茯苓桂枝甘草大枣汤")
        self.assertEqual(evidence["review_level"], "完整")
        names = [row["name"] for row in evidence["symptoms"]]
        self.assertIn("发汗后", names)
        self.assertIn("脐下悸", names)
        self.assertIn("欲作奔豚", names)
        self.assertIn("茯苓半斤", evidence["formula_original"]["text"])
        self.assertIn("桂枝四两", evidence["formula_original"]["text"])
        self.assertIn("大枣十五枚", evidence["formula_original"]["text"])
        self.assertIn("甘烂水一斗", evidence["usage_original"]["text"])
        self.assertIn("先煮茯苓", evidence["usage_original"]["text"])
        self.assertEqual(evidence["page_reading"][0]["page"], 51)
        self.assertIn("茯苓", evidence["rationale"]["full_text"])
        self.assertIn("大枣", evidence["rationale"]["full_text"])
        self.assertIn("奔豚", evidence["rationale"]["full_text"])
        self.assertIn("茯苓半斤", evidence["proofreading"][1]["note"])
        self.assertIn("大枣十五枚", evidence["proofreading"][1]["note"])

    def test_fuling_guizhi_baizhu_gancao_formula_is_fully_reviewed(self):
        data = self.client.get("/api/formulas/shanghan%3A%E8%8C%AF%E8%8B%93%E6%A1%82%E6%9E%9D%E7%99%BD%E6%9C%AF%E7%94%98%E8%8D%89%E6%B1%A4").json()
        evidence = data["evidence"]
        self.assertEqual(data["name"], "茯苓桂枝白术甘草汤")
        self.assertEqual(evidence["review_level"], "完整")
        names = [row["name"] for row in evidence["symptoms"]]
        for name in ("心下逆满", "气上冲胸", "起则头眩", "脉沉紧", "身为振振摇"):
            self.assertIn(name, names)
        self.assertIn("茯苓四两", evidence["formula_original"]["text"])
        self.assertIn("白朮二两", evidence["formula_original"]["text"])
        self.assertIn("桂枝三两", evidence["formula_original"]["text"])
        self.assertIn("以水六升", evidence["usage_original"]["text"])
        self.assertIn("分温三服", evidence["usage_original"]["text"])
        self.assertEqual(evidence["page_reading"][0]["page"], 53)
        self.assertIn("中膈", evidence["rationale"]["full_text"])
        self.assertIn("茯苓", evidence["rationale"]["full_text"])
        self.assertIn("白朮", evidence["rationale"]["full_text"])
        self.assertIn("起则头眩", evidence["rationale"]["full_text"])
        self.assertIn("茯苓四两", evidence["proofreading"][1]["note"])
        self.assertIn("白朮二两", evidence["proofreading"][1]["note"])

    def test_shaoyao_gancao_fuzi_formula_is_fully_reviewed(self):
        data = self.client.get("/api/formulas/shanghan%3A%E8%8A%8D%E8%8D%AF%E7%94%98%E8%8D%89%E9%99%84%E5%AD%90%E6%B1%A4").json()
        evidence = data["evidence"]
        self.assertEqual(data["name"], "芍药甘草附子汤")
        self.assertEqual(evidence["review_level"], "完整")
        names = [row["name"] for row in evidence["symptoms"]]
        for name in ("发汗后", "病不解", "反恶寒", "脚挛急", "脚冷"):
            self.assertIn(name, names)
        self.assertIn("芍药三两", evidence["formula_original"]["text"])
        self.assertIn("甘草三两炙", evidence["formula_original"]["text"])
        self.assertIn("附子一枚", evidence["formula_original"]["text"])
        self.assertIn("以水五升", evidence["usage_original"]["text"])
        self.assertIn("分温三服", evidence["usage_original"]["text"])
        self.assertEqual(evidence["page_reading"][0]["page"], 54)
        self.assertIn("阳虚", evidence["rationale"]["full_text"])
        self.assertIn("附子", evidence["rationale"]["full_text"])
        self.assertIn("芍药", evidence["rationale"]["full_text"])
        self.assertIn("芍药三两", evidence["proofreading"][1]["note"])
        self.assertIn("附子一枚", evidence["proofreading"][1]["note"])
        self.assertIn("疑非仲景方", evidence["proofreading"][1]["note"])

    def test_fuling_sini_formula_is_fully_reviewed(self):
        data = self.client.get("/api/formulas/shanghan%3A%E8%8C%AF%E8%8B%93%E5%9B%9B%E9%80%86%E6%B1%A4").json()
        evidence = data["evidence"]
        self.assertEqual(data["name"], "茯苓四逆汤")
        self.assertEqual(evidence["review_level"], "完整")
        names = [row["name"] for row in evidence["symptoms"]]
        for name in ("发汗若下", "病仍不解", "烦躁", "四逆"):
            self.assertIn(name, names)
        self.assertIn("茯苓四两", evidence["formula_original"]["text"])
        self.assertIn("人参一两", evidence["formula_original"]["text"])
        self.assertIn("附子一枚生用", evidence["formula_original"]["text"])
        self.assertIn("甘草二两炙", evidence["formula_original"]["text"])
        self.assertIn("干姜一两半", evidence["formula_original"]["text"])
        self.assertIn("以水五升", evidence["usage_original"]["text"])
        self.assertIn("温服七合", evidence["usage_original"]["text"])
        self.assertEqual(evidence["page_reading"][0]["page"], 55)
        self.assertIn("阴阳两虚", evidence["rationale"]["full_text"])
        self.assertIn("茯苓", evidence["rationale"]["full_text"])
        self.assertIn("人参", evidence["rationale"]["full_text"])
        self.assertIn("四逆汤", evidence["rationale"]["full_text"])
        self.assertIn("茯苓四两", evidence["proofreading"][1]["note"])
        self.assertIn("人参一两", evidence["proofreading"][1]["note"])
        self.assertIn("生附子一枚", evidence["proofreading"][1]["note"])

    def test_wuling_san_formula_is_fully_reviewed(self):
        data = self.client.get("/api/formulas/shanghan%3A%E4%BA%94%E8%8B%93%E6%95%A3").json()
        evidence = data["evidence"]
        self.assertEqual(data["name"], "五苓散")
        self.assertEqual(evidence["review_level"], "完整")
        names = [row["name"] for row in evidence["symptoms"]]
        for name in ("大汗出", "胃中干", "脉浮", "小便不利", "微热", "消渴"):
            self.assertIn(name, names)
        self.assertIn("猪苓十八铢", evidence["formula_original"]["text"])
        self.assertIn("泽泻一两六铢", evidence["formula_original"]["text"])
        self.assertIn("茯苓十八铢", evidence["formula_original"]["text"])
        self.assertIn("桂枝半两", evidence["formula_original"]["text"])
        self.assertIn("白饮和服方寸匕", evidence["usage_original"]["text"])
        self.assertIn("多饮暖水", evidence["usage_original"]["text"])
        self.assertIn("汗出愈", evidence["usage_original"]["text"])
        self.assertEqual(evidence["page_reading"][0]["page"], 56)
        self.assertIn("水蓄", evidence["rationale"]["full_text"])
        self.assertIn("小便不利", evidence["rationale"]["full_text"])
        self.assertIn("五苓散", evidence["rationale"]["full_text"])
        self.assertIn("猪苓十八铢", evidence["proofreading"][1]["note"])
        self.assertIn("泽泻一两六铢", evidence["proofreading"][1]["note"])

    def test_fuling_gancao_formula_is_fully_reviewed(self):
        data = self.client.get("/api/formulas/shanghan%3A%E8%8C%AF%E8%8B%93%E7%94%98%E8%8D%89%E6%B1%A4").json()
        evidence = data["evidence"]
        self.assertEqual(data["name"], "茯苓甘草汤")
        self.assertEqual(evidence["review_level"], "完整")
        names = [row["name"] for row in evidence["symptoms"]]
        for name in ("汗出", "不渴", "心下悸", "厥"):
            self.assertIn(name, names)
        self.assertIn("茯苓二两", evidence["formula_original"]["text"])
        self.assertIn("桂枝二两", evidence["formula_original"]["text"])
        self.assertIn("甘草一两", evidence["formula_original"]["text"])
        self.assertIn("生姜三两", evidence["formula_original"]["text"])
        self.assertIn("以水四升", evidence["usage_original"]["text"])
        self.assertIn("分温三服", evidence["usage_original"]["text"])
        self.assertEqual(evidence["page_reading"][0]["page"], 58)
        self.assertEqual(evidence["page_reading"][1]["page"], 199)
        self.assertIn("先治水", evidence["rationale"]["full_text"])
        self.assertIn("茯苓", evidence["rationale"]["full_text"])
        self.assertIn("心下悸", evidence["rationale"]["full_text"])
        self.assertIn("茯苓二两", evidence["proofreading"][1]["note"])
        self.assertIn("厥而心下悸", evidence["proofreading"][1]["note"])

    def test_zhizi_chi_formula_is_fully_reviewed(self):
        data = self.client.get("/api/formulas/shanghan%3A%E6%A0%80%E5%AD%90%E8%B1%89%E6%B1%A4").json()
        evidence = data["evidence"]
        self.assertEqual(data["name"], "栀子豉汤")
        self.assertEqual(evidence["review_level"], "完整")
        names = [row["name"] for row in evidence["symptoms"]]
        for name in ("虚烦不得眠", "反复颠倒", "心中懊憹"):
            self.assertIn(name, names)
        self.assertIn("栀子十四个", evidence["formula_original"]["text"])
        self.assertIn("香豉四合", evidence["formula_original"]["text"])
        self.assertIn("以水四升", evidence["usage_original"]["text"])
        self.assertIn("先煮栀子", evidence["usage_original"]["text"])
        self.assertIn("得吐者", evidence["usage_original"]["text"])
        self.assertEqual(evidence["page_reading"][0]["page"], 60)
        self.assertIn("虚热", evidence["rationale"]["full_text"])
        self.assertIn("栀子", evidence["rationale"]["full_text"])
        self.assertIn("豆豉", evidence["rationale"]["full_text"])
        self.assertIn("得吐者", evidence["rationale"]["full_text"])
        self.assertIn("栀子十四个", evidence["proofreading"][1]["note"])
        self.assertIn("香豉四合", evidence["proofreading"][1]["note"])

    def test_zhizi_gancao_chi_formula_is_fully_reviewed(self):
        data = self.client.get("/api/formulas/shanghan%3A%E6%A0%80%E5%AD%90%E7%94%98%E8%8D%89%E8%B1%89%E6%B1%A4").json()
        evidence = data["evidence"]
        self.assertEqual(data["name"], "栀子甘草豉汤")
        self.assertEqual(evidence["review_level"], "完整")
        names = [row["name"] for row in evidence["symptoms"]]
        self.assertIn("虚烦不得眠", names)
        self.assertIn("少气", names)
        self.assertIn("栀子十四个", evidence["formula_original"]["text"])
        self.assertIn("甘草二两炙", evidence["formula_original"]["text"])
        self.assertIn("香豉四合", evidence["formula_original"]["text"])
        self.assertIn("先煮栀子甘草", evidence["usage_original"]["text"])
        self.assertIn("得吐者止后服", evidence["usage_original"]["text"])
        self.assertEqual(evidence["page_reading"][0]["page"], 60)
        self.assertEqual(evidence["page_reading"][1]["page"], 61)
        self.assertIn("少气", evidence["rationale"]["full_text"])
        self.assertIn("甘草", evidence["rationale"]["full_text"])
        self.assertIn("补中", evidence["rationale"]["full_text"])
        self.assertIn("甘草二两", evidence["proofreading"][1]["note"])
        self.assertIn("栀子十四个", evidence["proofreading"][1]["note"])

    def test_zhizi_shengjiang_chi_formula_is_fully_reviewed(self):
        data = self.client.get("/api/formulas/shanghan%3A%E6%A0%80%E5%AD%90%E7%94%9F%E5%A7%9C%E8%B1%89%E6%B1%A4").json()
        evidence = data["evidence"]
        self.assertEqual(data["name"], "栀子生姜豉汤")
        self.assertEqual(evidence["review_level"], "完整")
        names = [row["name"] for row in evidence["symptoms"]]
        self.assertIn("虚烦不得眠", names)
        self.assertIn("呕", names)
        self.assertIn("栀子十四个", evidence["formula_original"]["text"])
        self.assertIn("生姜五两", evidence["formula_original"]["text"])
        self.assertIn("香豉四合", evidence["formula_original"]["text"])
        self.assertIn("先煮栀子生姜", evidence["usage_original"]["text"])
        self.assertIn("得吐者止后服", evidence["usage_original"]["text"])
        self.assertEqual(evidence["page_reading"][0]["page"], 60)
        self.assertEqual(evidence["page_reading"][1]["page"], 61)
        self.assertIn("呕", evidence["rationale"]["full_text"])
        self.assertIn("生姜", evidence["rationale"]["full_text"])
        self.assertIn("宣通", evidence["rationale"]["full_text"])
        self.assertIn("生姜五两", evidence["proofreading"][1]["note"])
        self.assertIn("栀子十四个", evidence["proofreading"][1]["note"])

    def test_zhizi_houpo_formula_is_fully_reviewed(self):
        data = self.client.get("/api/formulas/shanghan%3A%E6%A0%80%E5%AD%90%E5%8E%9A%E6%9C%B4%E6%B1%A4").json()
        evidence = data["evidence"]
        self.assertEqual(data["name"], "栀子厚朴汤")
        self.assertEqual(evidence["review_level"], "完整")
        names = [row["name"] for row in evidence["symptoms"]]
        for name in ("心烦", "腹满", "卧起不安"):
            self.assertIn(name, names)
        self.assertIn("栀子十四个", evidence["formula_original"]["text"])
        self.assertIn("枳实四枚", evidence["formula_original"]["text"])
        self.assertIn("厚朴四两", evidence["formula_original"]["text"])
        self.assertIn("以水三升半", evidence["usage_original"]["text"])
        self.assertIn("得吐者止后服", evidence["usage_original"]["text"])
        self.assertEqual(evidence["page_reading"][0]["page"], 61)
        self.assertEqual(evidence["page_reading"][1]["page"], 62)
        self.assertIn("心烦", evidence["rationale"]["full_text"])
        self.assertIn("腹满", evidence["rationale"]["full_text"])
        self.assertIn("厚朴", evidence["rationale"]["full_text"])
        self.assertIn("枳实", evidence["rationale"]["full_text"])
        self.assertIn("枳实四枚", evidence["proofreading"][1]["note"])
        self.assertIn("厚朴四两", evidence["proofreading"][1]["note"])
        self.assertIn("枳实四合", evidence["proofreading"][1]["note"])

    def test_zhizi_ganjiang_formula_is_fully_reviewed(self):
        data = self.client.get("/api/formulas/shanghan%3A%E6%A0%80%E5%AD%90%E5%B9%B2%E5%A7%9C%E6%B1%A4").json()
        evidence = data["evidence"]
        self.assertEqual(data["name"], "栀子干姜汤")
        self.assertEqual(evidence["review_level"], "完整")
        names = [row["name"] for row in evidence["symptoms"]]
        for name in ("丸药大下", "身热不去", "微烦"):
            self.assertIn(name, names)
        self.assertIn("栀子十四个", evidence["formula_original"]["text"])
        self.assertIn("干姜一两", evidence["formula_original"]["text"])
        self.assertIn("以水三升半", evidence["usage_original"]["text"])
        self.assertIn("得吐者止后服", evidence["usage_original"]["text"])
        self.assertEqual(evidence["page_reading"][0]["page"], 62)
        self.assertIn("上焦", evidence["rationale"]["full_text"])
        self.assertIn("中焦", evidence["rationale"]["full_text"])
        self.assertIn("栀子", evidence["rationale"]["full_text"])
        self.assertIn("干姜", evidence["rationale"]["full_text"])
        self.assertIn("栀子十四个", evidence["proofreading"][1]["note"])
        self.assertIn("干姜一两", evidence["proofreading"][1]["note"])
        self.assertIn("干姜二两", evidence["proofreading"][1]["note"])
        self.assertIn("香豉四合", evidence["proofreading"][1]["note"])

    def test_zhenwu_formula_is_fully_reviewed(self):
        data = self.client.get("/api/formulas/shanghan%3A%E7%9C%9F%E6%AD%A6%E6%B1%A4").json()
        evidence = data["evidence"]
        self.assertEqual(data["name"], "真武汤")
        self.assertEqual(evidence["review_level"], "完整")
        self.assertEqual(evidence["six_channel"]["id"], "shaoyin")
        names = [row["name"] for row in evidence["symptoms"]]
        for name in ("汗出不解", "仍发热", "心下悸", "头眩", "身瞤动", "振振欲擗地"):
            self.assertIn(name, names)
        self.assertIn("茯苓三两", evidence["formula_original"]["text"])
        self.assertIn("芍药三两", evidence["formula_original"]["text"])
        self.assertIn("白术二两", evidence["formula_original"]["text"])
        self.assertIn("生姜三两", evidence["formula_original"]["text"])
        self.assertIn("附子一枚", evidence["formula_original"]["text"])
        self.assertIn("以水八升", evidence["usage_original"]["text"])
        self.assertIn("温服七合", evidence["usage_original"]["text"])
        self.assertEqual(evidence["page_reading"][0]["page"], 63)
        self.assertEqual(evidence["page_reading"][1]["page"], 64)
        self.assertIn("阳虚水泛", evidence["rationale"]["full_text"])
        self.assertIn("附子", evidence["rationale"]["full_text"])
        self.assertIn("茯苓", evidence["rationale"]["full_text"])
        self.assertIn("不用甘草", evidence["rationale"]["full_text"])
        self.assertIn("茯苓三两", evidence["proofreading"][1]["note"])
        self.assertIn("白术二两", evidence["proofreading"][1]["note"])
        self.assertIn("附子一枚炮", evidence["proofreading"][1]["note"])

    def test_tongmai_sini_formula_is_fully_reviewed(self):
        data = self.client.get("/api/formulas/shanghan%3A%E9%80%9A%E8%84%89%E5%9B%9B%E9%80%86%E6%B1%A4").json()
        evidence = data["evidence"]
        self.assertEqual(data["name"], "通脉四逆汤")
        self.assertEqual(evidence["review_level"], "完整")
        self.assertEqual(evidence["six_channel"]["id"], "shaoyin")
        names = [row["name"] for row in evidence["symptoms"]]
        for name in ("下利清谷", "里寒外热", "手足厥逆", "脉微欲绝", "身反不恶寒", "面色赤"):
            self.assertIn(name, names)
        self.assertIn("甘草二两", evidence["formula_original"]["text"])
        self.assertIn("干姜三两", evidence["formula_original"]["text"])
        self.assertIn("附子大者一枚", evidence["formula_original"]["text"])
        self.assertIn("以水三升", evidence["usage_original"]["text"])
        self.assertIn("其脉即出者愈", evidence["usage_original"]["text"])
        self.assertEqual(evidence["page_reading"][0]["page"], 184)
        self.assertEqual(evidence["page_reading"][1]["page"], 185)
        self.assertEqual(evidence["page_reading"][2]["page"], 186)
        self.assertIn("里寒外热", evidence["rationale"]["full_text"])
        self.assertIn("阴盛格阳", evidence["rationale"]["full_text"])
        self.assertIn("通脉", evidence["rationale"]["full_text"])
        self.assertIn("甘草二两", evidence["proofreading"][1]["note"])
        self.assertIn("干姜三两", evidence["proofreading"][1]["note"])
        self.assertIn("附子大者一枚", evidence["proofreading"][1]["note"])

    def test_sini_san_formula_is_fully_reviewed(self):
        data = self.client.get("/api/formulas/shanghan%3A%E5%9B%9B%E9%80%86%E6%95%A3").json()
        evidence = data["evidence"]
        self.assertEqual(data["name"], "四逆散")
        self.assertEqual(evidence["review_level"], "完整")
        self.assertEqual(evidence["six_channel"]["id"], "shaoyin")
        names = [row["name"] for row in evidence["symptoms"]]
        for name in ("四逆", "咳", "悸", "小便不利", "腹中痛", "泄利下重"):
            self.assertIn(name, names)
        self.assertIn("甘草（炙）", evidence["formula_original"]["text"])
        self.assertIn("枳实（破水渍炙干）", evidence["formula_original"]["text"])
        self.assertIn("柴胡", evidence["formula_original"]["text"])
        self.assertIn("芍药", evidence["formula_original"]["text"])
        self.assertIn("各十分", evidence["formula_original"]["text"])
        self.assertIn("捣筛", evidence["usage_original"]["text"])
        self.assertIn("白饮和服方寸匕", evidence["usage_original"]["text"])
        self.assertIn("日三服", evidence["usage_original"]["text"])
        self.assertIn("薤白三升", evidence["usage_original"]["text"])
        self.assertIn("四味药等量捣成粉", evidence["usage_modern"]["source_text"])
        self.assertIn("米汤来服", evidence["usage_modern"]["source_text"])
        self.assertEqual(evidence["page_reading"][0]["page"], 186)
        self.assertEqual(evidence["page_reading"][1]["page"], 187)
        self.assertIn("阳气内郁", evidence["rationale"]["full_text"])
        self.assertIn("不是四逆汤", evidence["rationale"]["full_text"])
        self.assertIn("各十分", evidence["proofreading"][1]["note"])
        self.assertIn("白饮和服", evidence["proofreading"][1]["note"])
        self.assertIn("薤白三升", evidence["proofreading"][1]["note"])

    def test_zhuling_tang_formula_is_fully_reviewed(self):
        data = self.client.get("/api/formulas/shanghan%3A%E7%8C%AA%E8%8B%93%E6%B1%A4").json()
        evidence = data["evidence"]
        self.assertEqual(data["name"], "猪苓汤")
        self.assertEqual(evidence["review_level"], "完整")
        self.assertEqual(evidence["six_channel"]["id"], "yangming")
        self.assertIn("少阴病", evidence["six_channel"]["name"])
        names = [row["name"] for row in evidence["symptoms"]]
        for name in ("脉浮", "发热", "渴欲饮水", "小便不利", "下利", "咳", "呕", "心烦不得眠"):
            self.assertIn(name, names)
        self.assertIn("猪苓（去皮）", evidence["formula_original"]["text"])
        self.assertIn("滑石（碎）", evidence["formula_original"]["text"])
        self.assertIn("茯苓", evidence["formula_original"]["text"])
        self.assertIn("阿胶", evidence["formula_original"]["text"])
        self.assertIn("泽泻", evidence["formula_original"]["text"])
        self.assertIn("各一两", evidence["formula_original"]["text"])
        self.assertIn("以水四升", evidence["usage_original"]["text"])
        self.assertIn("纳阿胶烊消", evidence["usage_original"]["text"])
        self.assertIn("温服七合", evidence["usage_original"]["text"])
        self.assertEqual(evidence["page_reading"][0]["page"], 148)
        self.assertEqual(evidence["page_reading"][1]["page"], 149)
        self.assertEqual(evidence["page_reading"][2]["page"], 150)
        self.assertEqual(evidence["page_reading"][3]["page"], 187)
        self.assertIn("水热互结", evidence["rationale"]["full_text"])
        self.assertIn("阿胶", evidence["rationale"]["full_text"])
        self.assertIn("五苓散", evidence["rationale"]["full_text"])
        self.assertIn("真武汤", evidence["rationale"]["full_text"])
        self.assertIn("茯苓二两", evidence["proofreading"][1]["note"])
        self.assertIn("辑义各一两", evidence["proofreading"][1]["note"])
        self.assertIn("汗多", evidence["proofreading"][1]["note"])

    def test_mijian_formula_is_fully_reviewed(self):
        data = self.client.get("/api/formulas/shanghan%3A%E8%9C%9C%E7%85%8E").json()
        evidence = data["evidence"]
        self.assertEqual(data["name"], "蜜煎")
        self.assertEqual(evidence["review_level"], "完整")
        self.assertEqual(evidence["six_channel"]["id"], "yangming")
        names = [row["name"] for row in evidence["symptoms"]]
        for name in ("自汗出", "发汗", "小便自利", "津液内竭", "大便硬", "自欲大便"):
            self.assertIn(name, names)
        self.assertIn("食蜜（七合）", evidence["formula_original"]["text"])
        self.assertIn("铜器内", evidence["formula_original"]["text"])
        self.assertIn("微火煎", evidence["formula_original"]["text"])
        self.assertIn("凝如饴状", evidence["formula_original"]["text"])
        self.assertIn("捻作挺", evidence["formula_original"]["text"])
        self.assertIn("长二寸许", evidence["formula_original"]["text"])
        self.assertIn("纳谷道中", evidence["usage_original"]["text"])
        self.assertEqual(evidence["page_reading"][0]["page"], 152)
        self.assertEqual(evidence["page_reading"][1]["page"], 163)
        self.assertIn("津液内竭", evidence["rationale"]["full_text"])
        self.assertIn("不是结热", evidence["rationale"]["full_text"])
        self.assertIn("不可攻", evidence["rationale"]["full_text"])
        self.assertIn("七合", evidence["proofreading"][1]["note"])
        self.assertIn("铜器", evidence["proofreading"][1]["note"])
        self.assertIn("长二寸许", evidence["proofreading"][1]["note"])

    def test_herb_detail_has_formula_links(self):
        data = self.client.get("/api/herbs/bencao%3A%E7%89%A1%E6%A1%82").json()
        self.assertEqual(data["name"], "牡桂")
        self.assertTrue(any(item["name"] == "桂枝汤" for item in data["formulas"]))

    def test_search_and_filter(self):
        data = self.client.get("/api/formulas?q=桂枝&type=汤&page_size=60").json()
        self.assertGreater(data["total"], 0)
        self.assertTrue(all(item["name"] for item in data["items"]))
        self.assertTrue(all(item["type"] == "汤" for item in data["items"]))

    def test_source_variant_is_flagged(self):
        data = self.client.get("/api/overview").json()
        self.assertEqual(data["by_status"]["variant"], 4)
        self.assertEqual(data["by_status"]["missing"], 1)

    def test_six_channel_module_starts_with_taiyang(self):
        data = self.client.get("/api/six-channels").json()
        self.assertEqual(len(data["items"]), 6)
        taiyang = self.client.get("/api/six-channels/taiyang").json()
        self.assertEqual(taiyang["name"], "太阳病")
        self.assertEqual(taiyang["status"], "reviewed")
        self.assertGreaterEqual(len(taiyang["original"]), 3)
        self.assertGreaterEqual(len(taiyang["annotations"]), 3)
        self.assertIn("shanghan:桂枝汤", taiyang["related_formula_ids"])

    def test_every_formula_has_a_navigable_module(self):
        modules = json.loads((ROOT / "data" / "formula_modules.json").read_text(encoding="utf-8"))
        self.assertEqual(len(modules), 299)
        self.assertTrue(all(module.get("page_reading") for module in modules.values()))
        self.assertTrue(all(module.get("usage_original") for module in modules.values()))
        self.assertTrue(all(module.get("usage_modern") for module in modules.values()))

    def test_jinkui_is_present_and_marked(self):
        data = self.client.get("/api/formulas?book=金匮要略&page_size=60").json()
        self.assertEqual(data["total"], 186)
        detail = self.client.get("/api/formulas/jinkui%3A%E5%9B%9B%E9%80%86%E5%8A%A0%E4%BA%BA%E5%8F%82%E6%B1%A4").json()
        self.assertEqual(detail["name"], "四逆加人参汤")
        self.assertEqual(detail["evidence"]["review_status"], "reviewed")
        self.assertIn("视频同步文稿", detail["evidence"]["usage_note"])
        jinkui = json.loads((ROOT / "data" / "jinkui_formulas.json").read_text(encoding="utf-8"))
        self.assertEqual(sum(1 for item in jinkui if any(not row["dose"] for row in item["ingredients"])), 0)
        self.assertEqual(sum(1 for item in jinkui if item["status"] == "complete"), 168)
        self.assertEqual(sum(1 for item in jinkui if item["status"] == "unchecked"), 17)


if __name__ == "__main__":
    unittest.main()
