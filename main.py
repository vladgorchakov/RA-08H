from lorawan import RA08H


def main():
    ra = RA08H('COM7', 9600)
    # print(ra.read_manufacturer_identification())
    # print(ra.read_model_identification())
    # print(ra.read_version_identification())
    # print(ra.read_product_sequence_number())
    # print(ra.read_join_mode())
    # print(ra.set_join_mode('ABP'))
    # print(ra.set_dev_eui("1000000030000005"))
    # print(ra.read_dev_eui())
    # print(ra.set_app_eui("0000000000000099"))
    # print(ra.read_app_eui())
    # print(ra.set_app_key("20000000000000000000000000000004"))
    # print(ra.read_app_key())
    print(ra.set_dev_addr("007E6AE1"))
    print(ra.read_dev_addr())
    print(ra.read_apps_key())

if __name__ == "__main__":
    main()
